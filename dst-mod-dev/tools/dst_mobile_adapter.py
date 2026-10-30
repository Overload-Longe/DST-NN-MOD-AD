# -*- coding: utf-8 -*-
"""
柠版（手机端 DST）Mod 一键适配工具
==================================
对一个 PC 端 DST Mod（目录或 zip）一键完成：
  1. 纹理转换：DXT5 / RGBA → ASTC 8x8 单 mip（KTEX compression=24，Mali GPU 原生支持）
     - 自动检测"假转换"（header=4 但数据仍 DXT5 的多 mip 链），逐 mip 真解压
     - 无 astcenc 时自动回退为 RGBA（compression=4）
  2. 资源副本：anim/ images/ minimap/ modicon sound/ → scripts/mods/<mod名>/
  3. 自动文件生成：mod_auto.lua / early_prefab_auto.lua / preload_assets_auto.lua /
     sound_banks_auto.lua（有 sound 时）/ tile_preload_auto.lua（有 levels 自定义地形时）/
     test.lua（新 .lua 统一 UTF-8 BOM + CRLF；sound_banks/tile_preload 无 BOM + CRLF）
  4. 兼容层注入：生成 scripts/mobile_compat_<modkey>.lua 并注入 modmain.lua
     （3 处：开头 import / 资源预制物声明后 RegisterFW / 末尾 FinishLoad，幂等）
     - 可选 AddRecipe2 全局接管：手机端优先走 FW_RegisterRecipe（保守模式，不抢已有配方）
  5. 打包（可选 --zip）：zip 内套一层 <mod名> 文件夹，解压即得可直接拷贝的文件夹

用法:
  python dst_mobile_adapter.py <mod目录或zip> [选项]

选项:
  --out <目录>        输出目录（默认 <输入同级>/<mod名>-柠版适配版）
  --in-place          直接处理原目录（默认复制到输出目录，安全）
  --zip               处理完打包 zip（内套一层 mod 文件夹）
  --no-tex            跳过纹理转换
  --no-compat         跳过兼容层生成与 modmain 注入
  --no-recipes        兼容层里不接管 AddRecipe2
  --id <workshop-xxx> 手动指定工坊 ID（用于 identity_aliases）
  --astcenc <exe>     手动指定 astcenc 可执行文件
  --sync-auto         只重生成自动文件（资源增删后修「注册表陈旧」，默认原地）
  --verify-auto       只体检自动文件与 anim/ 一致性（只读，有 ERROR 退出码 1）
  --prune-dev         删除运行时用不到的开发者残留（.autosave.zip / sound/source / .fdp）

幂等：重复运行安全（已有注入/副本自动跳过或重建）。
"""
import argparse, hashlib, os, re, shutil, struct, subprocess, sys, tempfile, zipfile, itertools
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
TOOL_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
TOOL_VERSION = '1.6.7'   # v1.6.7（2026-10-28）：新增 --sync-auto（只刷自动文件，修「注册表陈旧」）/ --verify-auto（自动文件一致性体检，深扫 anim/）/ --prune-dev（清 .autosave.zip 与 sound/source）；early_prefab 过滤 .autosave.zip 与无 build/anim 的空壳包，且无 scripts/prefabs 的纯素材 mod 也生成；preload_assets 不再写 .tex；转换结束自动跑一次自检。v1.6.6（2026-10-27）：modinfo.name 含路径分隔符（如 "虚空异界（泰拉）/Void Realm"）时污染 scripts/mods/ 前缀、输出目录名与 zip 内层目录 → 引入 mod_fs_name() 分离"显示名/目录身份名"；zip 条目改正斜杠。v1.6.5（2026-10-16）：mod_auto.lua 的 entrypoints["modworldgenmain.lua"] 改为按实际文件探测（原先硬编码 false，会让自定义世界生成静默失效）；v1.6.4（2026-10-05）：asset_case_aliases 死动画过滤 + --audit-aliases 跨 mod 撞键审计
KTEX_COMP_DXT1 = 0
KTEX_COMP_DXT5 = 2
KTEX_COMP_RGBA = 4
KTEX_COMP_ASTC_8x8 = 24


# ---------------------------------------------------------------------------
# KTEX 解析 / DXT5 解压 / ASTC 编码
# ---------------------------------------------------------------------------
def ktex_info(data):
    """返回 (header_uint32, compression, mipmap_count, mips[(w,h,pitch,data)]) 或 None
    KTEX 布局：集中 mip 表（全部 pre 在文件头），随后按序排列各 mip 数据。"""
    if len(data) < 8 or data[:4] != b'KTEX':
        return None
    hdr = struct.unpack('<I', data[4:8])[0]
    comp = (hdr >> 4) & 0x1F
    mip = (hdr >> 13) & 0x1F
    off = 8
    pres = []
    for _ in range(mip):
        if off + 10 > len(data):
            return None
        w, h, pitch, dsz = struct.unpack('<HHHI', data[off:off+10])
        pres.append((w, h, pitch, dsz))
        off += 10
    mips = []
    for w, h, pitch, dsz in pres:
        if off + dsz > len(data):
            return None
        mips.append((w, h, pitch, data[off:off+dsz]))
        off += dsz
    return hdr, comp, mip, mips


def _rgb565(c):
    return ((c >> 11) & 0x1F) * 255 // 31, ((c >> 5) & 0x3F) * 255 // 63, (c & 0x1F) * 255 // 31


def _dxt5_block(block):
    a0, a1 = block[0], block[1]
    ai = block[2] | (block[3] << 8) | (block[4] << 16) | (block[5] << 24) | (block[6] << 32) | (block[7] << 40)
    c0 = block[8] | (block[9] << 8)
    c1 = block[10] | (block[11] << 8)
    ci = block[12] | (block[13] << 8) | (block[14] << 16) | (block[15] << 24)
    if a0 > a1:
        alpha = (a0, a1, (6*a0+1*a1)//7, (5*a0+2*a1)//7, (4*a0+3*a1)//7, (3*a0+4*a1)//7, (2*a0+5*a1)//7, (1*a0+6*a1)//7)
    else:
        alpha = (a0, a1, (4*a0+1*a1)//5, (3*a0+2*a1)//5, (2*a0+3*a1)//5, (1*a0+4*a1)//5, 0, 255)
    r0, g0, b0 = _rgb565(c0)
    r1, g1, b1 = _rgb565(c1)
    if c0 > c1:
        r2, g2, b2 = (2*r0+r1)//3, (2*g0+g1)//3, (2*b0+b1)//3
        r3, g3, b3 = (r0+2*r1)//3, (g0+2*g1)//3, (b0+2*b1)//3
    else:
        r2, g2, b2 = (r0+r1)//2, (g0+g1)//2, (b0+b1)//2
        r3 = g3 = b3 = 0
    out = bytearray(64)
    for p in range(16):
        a = alpha[(ai >> (p*3)) & 7]
        ci2 = (ci >> (p*2)) & 3
        o = p * 4
        if ci2 == 0:
            out[o], out[o+1], out[o+2] = r0, g0, b0
        elif ci2 == 1:
            out[o], out[o+1], out[o+2] = r1, g1, b1
        elif ci2 == 2:
            out[o], out[o+1], out[o+2] = r2, g2, b2
        else:
            out[o], out[o+1], out[o+2] = r3, g3, b3
        out[o+3] = a
    return out


def dxt5_to_rgba(data, w, h):
    """DXT5 数据 -> RGBA 字节（BC3 软解压）。"""
    res = bytearray(w * h * 4)
    bw, bh = (w+3)//4, (h+3)//4
    for by in range(bh):
        y0 = by*4
        for bx in range(bw):
            x0 = bx*4
            off = (by*bw+bx)*16
            px = _dxt5_block(data[off:off+16])
            for py in range(4):
                y = y0+py
                if y >= h:
                    break
                dst = (y*w+x0)*4
                cw = min(4, w-x0)
                res[dst:dst+cw*4] = px[py*16:py*16+cw*4]
    return bytes(res)


def dxt1_to_rgba(data, w, h):
    """DXT1（BC1，KTEX comp=0）数据 -> RGBA 字节（4bpp 软解压）。
    block=8B：c0/c1 RGB565 + 32bit 2bpp 索引；c0>c1 四色插值，否则 3 色 + 全透明。"""
    res = bytearray(w * h * 4)
    bw, bh = (w+3)//4, (h+3)//4
    for by in range(bh):
        y0 = by*4
        for bx in range(bw):
            x0 = bx*4
            off = (by*bw+bx)*8
            if off + 8 > len(data):
                return None
            c0 = data[off] | (data[off+1] << 8)
            c1 = data[off+2] | (data[off+3] << 8)
            idx = data[off+4] | (data[off+5] << 8) | (data[off+6] << 16) | (data[off+7] << 24)
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)
            if c0 > c1:
                pal = ((r0, g0, b0, 255), (r1, g1, b1, 255),
                       ((2*r0+r1)//3, (2*g0+g1)//3, (2*b0+b1)//3, 255),
                       ((r0+2*r1)//3, (g0+2*g1)//3, (b0+2*b1)//3, 255))
            else:
                pal = ((r0, g0, b0, 255), (r1, g1, b1, 255),
                       ((r0+r1)//2, (g0+g1)//2, (b0+b1)//2, 255),
                       (0, 0, 0, 0))
            for p in range(16):
                y = y0 + p//4
                x = x0 + p%4
                if y >= h or x >= w:
                    continue
                pr, pg, pb, pa = pal[(idx >> (p*2)) & 3]
                o = (y*w+x)*4
                res[o] = pr; res[o+1] = pg; res[o+2] = pb; res[o+3] = pa
    return bytes(res)


def parse_mip0_rgba(data):
    """从 KTEX 取 mip0 真实 RGBA 数据（兼容：真 RGBA / 假转换的 DXT5 数据）。
    返回 (w, h, rgba_bytes) 或 None。"""
    info = ktex_info(data)
    if info is None:
        return None
    hdr, comp, mip, mips = info
    w, h, pitch, d0 = mips[0]
    if comp == KTEX_COMP_RGBA:
        if len(d0) == w*h*4:
            return w, h, d0
        # 假转换：header=4 但数据仍 DXT5
        try:
            return w, h, dxt5_to_rgba(d0, w, h)
        except Exception:
            return None
    if comp == KTEX_COMP_DXT5:
        try:
            return w, h, dxt5_to_rgba(d0, w, h)
        except Exception:
            return None
    if comp == 5:
        # LDR RGB 未压缩（colourcube 等：pitch=w*3，datasz=w*h*3）→ RGBA 补 A=255
        if len(d0) == w*h*3:
            rgba = bytearray(w*h*4)
            rgba[0::4] = d0[0::3]
            rgba[1::4] = d0[1::3]
            rgba[2::4] = d0[2::3]
            rgba[3::4] = b'\xff' * (w*h)
            return w, h, bytes(rgba)
        return None
    if comp == KTEX_COMP_DXT1:
        try:
            rgba = dxt1_to_rgba(d0, w, h)
            return (w, h, rgba) if rgba is not None else None
        except Exception:
            return None
    return None  # 已是 ASTC 或其它


def build_ktex_rgba(hdr, mips_rgba):
    """按 mips_rgba[(w,h,rgba)] 重建 RGBA KTEX（保留原 flags）。"""
    new_hdr = hdr & ~(0x1F << 4) & ~(0x1F << 13) | (KTEX_COMP_RGBA << 4) | (len(mips_rgba) << 13)
    out = b'KTEX' + struct.pack('<I', new_hdr)
    for w, h, rgba in mips_rgba:
        out += struct.pack('<HHHI', w, h, w*4, len(rgba))
    for w, h, rgba in mips_rgba:
        out += rgba
    return out


def find_astcenc(manual=None):
    cands = []
    if manual:
        cands.append(manual)
    env = os.environ.get('ASTCENC')
    if env:
        cands.append(env)
    for name in ('astcenc.exe', 'astcenc-avx2.exe', 'astcenc-sse4.1.exe', 'astcenc-sse2.exe'):
        p = os.path.join(TOOL_DIR, 'astcenc', name)
        if os.path.exists(p):
            cands.append(p)
    if os.path.isdir(os.path.join(TOOL_DIR, 'astcenc')):
        for n in os.listdir(os.path.join(TOOL_DIR, 'astcenc')):
            if n.endswith('.exe'):
                cands.append(os.path.join(TOOL_DIR, 'astcenc', n))
    tmp = os.environ.get('TEMP')
    if tmp:
        d = os.path.join(tmp, 'astcenc_dir', 'bin')
        if os.path.isdir(d):
            for n in os.listdir(d):
                if n.endswith('.exe'):
                    cands.append(os.path.join(d, n))
    sh = shutil.which('astcenc')
    if sh:
        cands.append(sh)
    seen = set()
    for c in cands:
        c = os.path.abspath(c)
        if c in seen:
            continue
        seen.add(c)
        if os.path.exists(c):
            return c
    return None


_CANCEL = False  # GUI 取消标志：置 True 后纹理转换/各阶段检查点中断（v1.4.22）


class TexConverter:
    """纹理转换器：RGBA/DXT5 → ASTC 8x8 单 mip；无 astcenc 时 → RGBA。"""

    def __init__(self, astcenc=None, prefer_astc=True, tmpdir=None):
        self.astcenc = astcenc
        self.prefer_astc = prefer_astc
        self.tmpdir = tmpdir or tempfile.mkdtemp(prefix='fwadapt_')
        self.converted = 0
        self.failed = []
        self._tmp_seq = itertools.count()  # 并发唯一临时文件序号（count.next 原子）

    def _astc_enc(self, w, h, rgba):
        # 并发安全：每次用唯一临时文件（多 worker 共用 t.png/t.astc 会互相覆盖 → 编码失败）
        uid = '%d_%d' % (os.getpid(), next(self._tmp_seq))
        png = os.path.join(self.tmpdir, 't%s.png' % uid)
        ast = os.path.join(self.tmpdir, 't%s.astc' % uid)
        try:
            from PIL import Image
            Image.frombytes('RGBA', (w, h), rgba).save(png)
            r = subprocess.run([self.astcenc, '-cs', png, ast, '8x8', '-medium', '-silent'],
                               capture_output=True,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if r.returncode != 0:
                return None
            body = open(ast, 'rb').read()
            if len(body) <= 16:
                return None
            return body[16:]  # 去 16B ASTC 文件头
        except Exception:
            return None
        finally:
            for fp in (png, ast):
                try:
                    os.remove(fp)
                except Exception:
                    pass

    def convert_bytes(self, data):
        """把任意 KTEX（DXT5/RGBA）转 ASTC(24) 或 RGBA(4) 单 mip。返回新字节或 None。"""
        info = ktex_info(data)
        if info is None:
            return None
        hdr, comp, mip, mips = info
        if comp == KTEX_COMP_ASTC_8x8:
            return None  # 已是目标
        m0 = parse_mip0_rgba(data)
        if m0 is None:
            return None
        w, h, rgba = m0
        if self.astcenc and self.prefer_astc:
            body = self._astc_enc(w, h, rgba)
            if body is not None:
                # ★ flags 高位与真实正常 mod 字节级一致（2878 个 mod tex 实测：
                #   bit20-31 = 0xFFF 固定工具链前缀，bit18-19=00 → bit18+ = 0x3FFC；
                #   v1.6.3 修复：ASTC 单 mip 完整 flags = 0xFFF02380（bit9=1）——
                #   柠版 2.1.1 成功 mod（更多料理 v3.44/AIP v3.40）全部 tex（含 anim
                #   zip 内部）逐字节实证 bit9=1 是 Mali 管线必需位（minimap 同标准）；
                #   旧值 0xFFF02180（bit9=0）虽能加载，但消除"格式可疑"类边缘问题。
                new_hdr = (0xFFF << 20) | (KTEX_COMP_ASTC_8x8 << 4) | (1 << 13) | (1 << 9)
                out = b'KTEX' + struct.pack('<I', new_hdr)
                out += struct.pack('<HHHI', w, h, 0, len(body))
                out += body
                return out
        # 回退 RGBA 单 mip（高位同补 0xFFF 前缀：0xFFF02040，与主流 RGBA 头一致）
        new_hdr = (0xFFF << 20) | (KTEX_COMP_RGBA << 4) | (1 << 13)
        out = b'KTEX' + struct.pack('<I', new_hdr)
        out += struct.pack('<HHHI', w, h, w*4, len(rgba))
        out += rgba
        return out

    def convert_file(self, path):
        """转换单个 .tex 文件。返回 (是否成功, 转换数)。并发安全（不写 self.converted）。"""
        try:
            with open(path, 'rb') as f:
                data = f.read()
            nd = self.convert_bytes(data)
            if nd is None:
                self.failed.append((path, 'convert_bytes=None（未知/不支持的 KTEX 格式）'))
                return False, 0
            with open(path, 'wb') as f:
                f.write(nd)
            return True, 1
        except Exception as e:
            self.failed.append((path, str(e)[:120]))
            return False, 0

    def convert_zip(self, path):
        """转换 .zip 内全部 .tex。返回转换数。并发安全（不写 self.converted）。"""
        try:
            zin = zipfile.ZipFile(path, 'r')
        except Exception:
            return 0
        items = [(it, zin.read(it.filename)) for it in zin.infolist()]
        zin.close()
        changed = False
        n = 0
        for i, (it, data) in enumerate(items):
            if it.filename.endswith('.tex'):
                nd = self.convert_bytes(data)
                if nd is not None:
                    items[i] = (it, nd)
                    n += 1
                    changed = True
        if changed:
            tmp = path + '.tmp'
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zo:
                for it, data in items:
                    zo.writestr(it, data)
            os.replace(tmp, path)
        return n

    def _convert_job(self, kind, path):
        """线程池 worker：转换单个 tex 或 zip。返回 (是否成功, 转换数)。"""
        try:
            if kind == 'tex':
                return self.convert_file(path)
            return True, self.convert_zip(path)
        except Exception as e:
            self.failed.append((path, str(e)[:120]))
            return False, 0

    def scan_and_convert(self, roots, progress=False, workers=None):
        """遍历目录转换所有独立 .tex 与 .zip 内 .tex（并发提速）。

        roots：目录路径或路径列表（自动跳过 scripts/、mods/ 子目录——避免递归到
        资源副本）。progress=True 时按完成数打印 PROGRESS:done/total（GUI 进度条
        解析用，并发下 done 递增即平滑）。
        workers：并发数，默认 min(CPU核, 6)（astcenc 内存开销，保守上限）。
        astcenc 为独立子进程 → 线程池仅作分发器，CPU 真正并行，无 GIL 瓶颈；
        线程方案规避 PyInstaller frozen exe 下 multiprocessing spawn 重跑主模块问题。
        返回统计 dict。"""
        if isinstance(roots, str):
            roots = [roots]
        stats = {'astc_already': 0, 'other': 0, 'converted': 0, 'failed': 0}
        job_map = {}  # 按路径去重（root 可能互相包含，如根目录 + anim/images 子目录）
        for root in roots:
            if not os.path.isdir(root):
                continue
            for r, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in ('scripts', 'mods')]
                for f in files:
                    p = os.path.join(r, f)
                    if f.endswith('.tex'):
                        try:
                            with open(p, 'rb') as fh:
                                h = fh.read(16)
                            if h[:4] == b'KTEX':
                                c = (struct.unpack('<I', h[4:8])[0] >> 4) & 0x1F
                                if c == KTEX_COMP_ASTC_8x8:
                                    stats['astc_already'] += 1
                                    continue
                        except Exception:
                            pass
                        job_map[p] = ('tex', p)
                    elif f.endswith('.zip'):
                        job_map.setdefault(p, ('zip', p))
        jobs = list(job_map.values())
        total = len(jobs)
        if not workers or workers <= 0:
            workers = min(os.cpu_count() or 4, 6)
        if total <= 1 or workers <= 1:
            # 串行路径（保留原行为）
            done = 0
            for kind, p in jobs:
                if _CANCEL:
                    print('== 已取消：纹理转换中断')
                    break
                ok, n = self._convert_job(kind, p)
                if ok:
                    stats['converted'] += n
                else:
                    stats['failed'] += 1
                done += 1
                if progress and total:
                    print('PROGRESS:%d/%d' % (done, total), flush=True)
            return stats
        done = 0
        ex = ThreadPoolExecutor(max_workers=workers)
        futs = {ex.submit(self._convert_job, kind, p): (kind, p) for kind, p in jobs}
        cancelled = False
        for fut in as_completed(futs):
            if _CANCEL:
                print('== 已取消：纹理转换中断')
                for f in futs:
                    f.cancel()
                cancelled = True
                break
            try:
                ok, n = fut.result()
            except Exception:
                ok, n = False, 0
            if ok:
                stats['converted'] += n
            else:
                stats['failed'] += 1
            done += 1
            if progress and total:
                print('PROGRESS:%d/%d' % (done, total), flush=True)
        ex.shutdown(wait=not cancelled, cancel_futures=cancelled)
        return stats


# ---------------------------------------------------------------------------
# modinfo 解析
# ---------------------------------------------------------------------------
def parse_modinfo(text, fallback_dirname='mod'):
    name = fallback_dirname
    version = ''
    modid = ''
    m = re.search(r'name\s*=\s*Lang\(\s*"[^"]*"\s*,\s*"([^"]+)"\s*\)', text)
    if m:
        name = m.group(1)
    else:
        # ★ 三元表达式 name = L and "英文" or "中文"（神话书说安卓版式，v1.6.1）
        #   取 or 分支（中文环境 L=false 时求值结果）
        m = re.search(r'name\s*=\s*L\s+and\s+"[^"]*"\s+or\s+"([^"]+)"', text)
        if m:
            name = m.group(1)
        else:
            # 行首 name（v1.6.1：不允许行尾逗号，排除配置项独立行 `name = "Language",`）
            m = re.search(r'(?m)^\s*name\s*=\s*"([^"]+)"\s*$', text)
            if m:
                name = m.group(1)
            else:
                # 多语言表（v1.6.0）：name = ChooseTranslationTable(STRINGS.NAME) → 提取英文名
                m = re.search(r'STRINGS\s*=\s*\{[^}]*?NAME\s*=\s*\{[^}]*?zh\s*=\s*"([^"]+)"', text, re.S)
                if m:
                    name = m.group(1)
                else:
                    m = re.search(r'STRINGS\s*=\s*\{[^}]*?NAME\s*=\s*\{[^}]*?"([^"]+)"', text, re.S)
                    if m:
                        name = m.group(1)
                    else:
                        # ★ 单引号 name（英雄联盟武器式：['zh'] = { name = '英雄联盟武器' }）
                        # 缺失时 modname 回退为解包目录名（如 3319931009）→ asset_case_aliases
                        # 前缀 scripts/mods/<数字>/... ≠ 框架 owner → invalid asset alias owner
                        m = re.search(r"name\s*=\s*'([^']+)'", text)
                        if m:
                            name = m.group(1)
    m = re.search(r'version\s*=\s*"([^"]+)"', text)
    if m:
        version = m.group(1)
    else:
        m = re.search(r"version\s*=\s*'([^']+)'", text)
        if m:
            version = m.group(1)
    m = re.search(r'id\s*=\s*"([^"]+)"', text)
    if m:
        modid = m.group(1)
    else:
        m = re.search(r"id\s*=\s*'([^']+)'", text)
        if m:
            modid = m.group(1)
    m = re.search(r'workshop[_-](\d+)', text)
    if m:
        modid = modid or ('workshop-' + m.group(1))
    return name.strip(), version.strip(), modid.strip()



def mod_fs_name(name, fallback='mod'):
    """modinfo.name → 可安全用作目录名 / FW 身份串的名字。

    modinfo.name 是**显示名**，可能含路径分隔符（如 "虚空异界（泰拉）/Void Realm"）。
    柠版框架里 mod 的 owner = mods 目录下的文件夹名，而
    `scripts/mods/<owner>/...` 前缀、FW_* 注册名、输出目录名、zip 内层目录
    都必须与它同构。直接拿显示名当目录名会变成两级子目录，
    框架报 invalid asset alias owner / 找不到 mod，zip 也是坏的（2026-10-27 虚空异界实证）。
    """
    s = (name or '').strip()
    if s:
        s = re.split(r'[\\/]+', s)[0].strip()        # 取斜杠前第一段
        s = re.sub(r'[<>:"|?*\x00-\x1f]', '_', s)    # Windows 目录非法字符
        s = s.rstrip(' .')                            # Windows 尾随空格/点
    return s or fallback


def modkey(name):
    s = re.sub(r'[^\x00-\x7f]', '', name)  # 去非 ASCII
    s = re.sub(r'[^\w]', '_', s.lower())
    return s.strip('_') or 'mod'


# ---------------------------------------------------------------------------
# 自动文件生成
# ---------------------------------------------------------------------------
def collect_anim_code_refs(modroot):
    """收集 mod 全部 Lua 源码中实际引用的动画名（zip 基本名），排除自动生成文件。

    v1.6.4 新增：用于过滤 asset_case_aliases 中的"零引用死动画"条目。别名表是
    框架全局合并（大小写不敏感），两个 mod 含同名动画 zip（如泰拉/传奇武器
    的 hh_slot_fx，2026-10-05 实证）即触发 ambiguous asset case alias 崩溃；
    源码零引用的死动画注册别名纯属占用全局表，删除无任何运行时影响。

    判定规则：zip 基本名（hh_slot_fx）以子串形式出现在任一 .lua 源码中即视为
    有引用（覆盖 SetBank/SetBuild/Asset("ANIM","anim/x.zip")/PlayAnimation 等
    字面量与路径形式）；排除工具生成的 mod_auto.lua / *_auto.lua / test.lua
    （它们会自引用全部 zip，导致过滤失效）。
    """
    chunks = []
    for r, dirs, files in os.walk(modroot):
        for f in files:
            if not f.endswith('.lua'):
                continue
            if f == 'mod_auto.lua' or f == 'test.lua' or f.endswith('_auto.lua'):
                continue
            p = os.path.join(r, f)
            try:
                chunks.append(open(p, encoding='utf-8', errors='replace').read())
            except Exception:
                continue
    blob = '\n'.join(chunks)
    refs = set()
    # 从源码字符串里提取候选动画名 token（含路径/拼接待查）
    for m in re.finditer(r'([A-Za-z0-9_]{2,64})\.zip', blob):
        refs.add(m.group(1))
    for m in re.finditer(r'["\']([A-Za-z0-9_]{2,64})["\']', blob):
        refs.add(m.group(1))
    return refs


def gen_mod_auto(modroot, modname, modid, native=False, anim_refs=None, display_name=None,
                 keep_identity=None):
    # modname = 目录身份名（scripts/mods/<modname>/ 前缀、框架 owner 校验用）
    # display_name = modinfo.name 原样（identity_aliases / autotest_suite 用）
    # keep_identity = 需要保留的既有 identity_aliases（★ v1.6.7：--sync-auto 没带 --id 时
    #   不能让已登记的 workshop-xxx 被冲掉 —— 丢了它，管理器/存档里同一个 mod 会被当新 mod）
    disp = display_name or modname
    aliases = {}
    if native:
        # 纯原生模式：别名值必须 scripts/mods/<mod名>/... 格式（框架按 owner 校验，
        # 否则 FrontendLoadMod 报 invalid asset alias owner）。目录不存在无害
        # （手工适配 mod 全是死引用，趣味食物/英雄联盟武器验证正常）。
        for sub in ('anim', 'images', 'minimap', 'sound', 'map'):
            sd = os.path.join(modroot, sub)
            if not os.path.isdir(sd):
                continue
            for r, dirs, files in os.walk(sd):
                for f in files:
                    rel = os.path.relpath(os.path.join(r, f), modroot).replace('\\', '/')
                    if (sub == 'anim' and anim_refs is not None and f.lower().endswith('.zip')
                            and os.path.splitext(f)[0] not in anim_refs):
                        continue  # ★ v1.6.4 死动画过滤：源码零引用，不注册别名防跨 mod 撞键
                    aliases[rel] = 'scripts/mods/%s/%s' % (modname, rel)
        # ★ 不注册 modicon.xml/.tex/.png 别名：手工正常版（英雄联盟武器/趣味食物/
        #   简易存储/棱镜等 39 个）的 mod_auto.lua 均无此键。多个工具转换的 mod
        #   同含 ["modicon.xml"] 键（大小写不敏感同名）→ 框架
        #   resources.assets:setup FAIL → ambiguous asset case alias: modicon.xml。
        #   modicon 由 preload_assets_auto.lua 路径清单预加载（手工版普遍含，无冲突）。
    else:
        mods_dir = os.path.join(modroot, 'scripts', 'mods', modname)
        if not os.path.isdir(mods_dir):
            return None
        for r, dirs, files in os.walk(mods_dir):
            for f in files:
                if f.startswith('modicon.'):
                    continue  # 同上：不注册 modicon 别名，防跨 mod ambiguous
                full = os.path.join(r, f)
                rel = os.path.relpath(full, mods_dir).replace('\\', '/')
                if (rel.startswith('anim/') and anim_refs is not None and f.lower().endswith('.zip')
                        and os.path.splitext(f)[0] not in anim_refs):
                    continue  # ★ v1.6.4 死动画过滤：同上
                aliases[rel] = 'scripts/mods/%s/%s' % (modname, rel)
    # ★ v1.6.5 修复（2026-10-16 实证）：entrypoints 原先硬编码 modservercreationmain/
    #   modworldgenmain = false，而柠版加载器**只认这份清单**（不作为则日志打
    #   "Mod had no modworldgenmain.lua. Skipping."，即使文件真实存在也绝不加载）。
    #   后果：凡带世界生成的 mod 适配后静默丢地图（创世纪：AddRoom/AddTask/
    #   AddTaskSetPreInit 全部没执行 → 月岛/世界树岛/宫殿岛不生成，其余功能正常，
    #   极易误判成"地图就是没有"）。且工具自身 8.405) 会给 modworldgenmain.lua
    #   的 modimport 链注入 _G 别名——本身就假定了它会被加载，前后矛盾。
    #   判据（对 APK 内置 mod 全量比对）：原版增强修复是唯一 entrypoints=true 的 mod，
    #   也是日志中唯一真正 "Loading modworldgenmain.lua" 的 mod。故按实际文件探测。
    _entry_roots = [modroot, os.path.join(modroot, 'scripts', 'mods', modname)]
    def _has_entry(fn):
        return any(os.path.exists(os.path.join(r, fn)) for r in _entry_roots)
    _wgm = _has_entry('modworldgenmain.lua')
    _scm = _has_entry('modservercreationmain.lua')
    lines = ['-- Generated automatically. Do not edit.', 'return {',
             '    entrypoints = {',
             '        ["modmain.lua"] = true,',
             '        ["modservercreationmain.lua"] = %s,' % ('true' if _scm else 'false'),
             '        ["modworldgenmain.lua"] = %s,' % ('true' if _wgm else 'false'),
             '    },',
             '    asset_case_aliases = {']
    for k in sorted(aliases):
        lines.append('        ["%s"] = "%s",' % (k, aliases[k]))
    lines.append('    },')
    lines.append('    identity_aliases = {')
    _ident = []
    if disp != modname:
        # modinfo.name 原样（含分隔符/前缀）也是同一 mod 的身份串
        _ident.append(disp)
    if modid:
        _ident.append(modid)
    for s in (keep_identity or []):
        if s and s not in _ident and s != modname:
            _ident.append(s)
    for s in _ident:
        lines.append('        "%s",' % s.replace('"', '\\"'))
    lines.append('    },')
    lines.append('    autotest_suite = {')
    lines.append('        id = "%s", mod = "%s",' % (modkey(disp), disp.replace('"', '\\"')))
    lines.append('    },')
    lines.append('}')
    return '\r\n'.join(lines) + '\r\n'


def audit_alias_conflicts(paths):
    """v1.6.4：扫描多个已适配 mod（目录或 zip）的 mod_auto.lua，
    报告 asset_case_aliases 跨 mod 撞键（ambiguous asset case alias 预检）。

    同 key（大小写不敏感）映射不同 value → 框架 resources.assets:setup
    FAIL → ambiguous asset case alias。同 key 同 value 不计（无害重复）。
    命中后按排障 SOP 处理：从功能次要方删除该别名条目（或删死动画文件）。
    """
    print('== asset_case_aliases 跨 mod 撞键审计 (v%s) ==' % TOOL_VERSION)
    entries = {}
    for p in paths:
        found = []
        if os.path.isdir(p):
            for r, dirs, files in os.walk(p):
                if 'mod_auto.lua' in files:
                    try:
                        txt = open(os.path.join(r, 'mod_auto.lua'), encoding='utf-8',
                                   errors='replace').read()
                    except Exception as e:
                        print('   [warn] 读取失败 %s: %s' % (p, e))
                        continue
                    found.append((os.path.basename(r.rstrip('/\\')) or os.path.basename(p), txt))
        else:
            try:
                z = zipfile.ZipFile(p)
            except Exception as e:
                print('   [warn] 无法打开 %s: %s' % (p, e))
                continue
            for n in z.namelist():
                if n.replace('\\', '/').lower().endswith('mod_auto.lua'):
                    try:
                        txt = z.read(n).decode('utf-8', errors='replace')
                    except Exception:
                        continue
                    top = n.replace('\\', '/').split('/')[0]
                    found.append((top, txt))
                    break
        if not found:
            print('   [warn] %s 未找到 mod_auto.lua' % p)
        for mod, txt in found:
            for m in re.finditer(r'\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', txt):
                entries.setdefault(m.group(1).lower(), []).append((mod, m.group(2)))
    amb = [(k, v) for k, v in sorted(entries.items()) if len(set(x[1] for x in v)) > 1]
    if not amb:
        print('  未发现跨 mod 歧义键（同 key 同值不计）。')
        return
    print('  发现 %d 个歧义键（同 key 不同 value，大小写不敏感）：' % len(amb))
    for k, v in amb:
        print('  key=%s' % k)
        for mod, val in v:
            print('     - %s -> %s' % (mod, val))


def is_dev_anim_zip(fname):
    """美术工具（Spine/手写导出脚本）自动备份包：`<name>.autosave.zip`。

    这类包是导出流程的中间产物，真实 mod 里没有任何 `SetBuild`/`Asset` 引用，
    注册进 early_prefab 只会白占 FW_EARLY_HOLDER 槽位（泰拉实例 8 个 / 0.88MB）。
    """
    return '.autosave.' in fname.lower()


def anim_zip_has_payload(path):
    """zip 内是否含 build.bin 或 anim.bin —— 两者都没有的包加载不到任何东西。

    实测反例：whip_snapthorn.zip 只含 atlas-0.tex，被 Asset("ANIM") 声明后
    resolvefilepath 能通过（文件在），但 build 永远建不起来 → 静默空模型。
    """
    try:
        with zipfile.ZipFile(path) as z:
            names = set(n.rsplit('/', 1)[-1].lower() for n in z.namelist())
    except Exception:
        return False
    return ('build.bin' in names) or ('anim.bin' in names)


def list_anim_zips(modroot, report=False):
    """返回 anim/ 下「应进 early 表」的 zip 列表（已剔除 .autosave 与空壳包）。"""
    d = os.path.join(modroot, 'anim')
    if not os.path.isdir(d):
        return []
    keep, skipped = [], []
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith('.zip'):
            continue
        p = os.path.join(d, f)
        if is_dev_anim_zip(f):
            skipped.append((f, '美术工具自动备份 .autosave.zip'))
            continue
        if not anim_zip_has_payload(p):
            skipped.append((f, '无 build.bin / anim.bin（加载不到任何东西）'))
            continue
        keep.append(f)
    if report:
        for f, why in skipped:
            print('    [skip] anim/%s —— %s' % (f, why))
    return keep


def gen_early_prefab(modroot, modname, native=False):
    if native:
        # ★ 纯原生模式：全量 build 注册（英雄联盟武器式，AIP 第十四轮实证）
        #   英雄联盟武器 early_prefab_auto.lua = 404 条含 109 条 swap 条目
        #   （name=build 名=zip 名去后缀）。框架按条目预注册 build→zip，
        #   SetBuild/OverrideSymbol 时 build 已在内存，swap/皮肤/主 build 全部显示。
        #   AIP 旧逻辑只注册 prefab 名→主动画（0 swap 条目）→ swap/皮肤 zip 从不
        #   加载 → 手持/穿戴/皮肤空白（用户 13-14 轮实证）。
        #   注意（v1.6.7 源码修正）：prefab/modmain 的 Asset("ANIM") 只让**路径能解析**，
        #   不保证 build 驻留内存 —— 漏注册的 build 全都声明过，照样世界内空白。
        #   注（v1.6.4）：early_prefab 保持全量注册（含零引用 zip），动画加载通道
        #   不受影响；跨 mod 撞键的清理由 gen_mod_auto 死动画过滤承担。
        #   注（v1.6.7）：① 骨架 OCR；② 纯素材 mod（无 scripts/prefabs）也要生成；
        #   ③ 过滤美术工具 .autosave.zip 与「无 build.bin 且无 anim.bin」的空包 ——
        #      这类包注册进去只会白占 FW_EARLY_HOLDER 槽位（泰拉 1032→1029 实战）。
        #   ★ 全量 = anim/ 下每个「可加载」zip 一条，与源码引用无关（框架契约）。
        anim_dir = os.path.join(modroot, 'anim')
        if not os.path.isdir(anim_dir):
            return None
        zips = list_anim_zips(modroot, report=True)
        if not zips:
            return None
        lines = ['-- Generated automatically. Do not edit.',
                 '-- 全量 build 注册（柠版 early_prefab 通道）：name=build名(无.zip后缀), anim=完整路径',
                 'return {']
        for z in zips:
            name = z[:-4]
            lines.append('    { name = "%s", anim = "scripts/mods/%s/anim/%s" },' % (name, modname, z))
        lines.append('}')
        return '\r\n'.join(lines) + '\r\n'
    prefab_dir = os.path.join(modroot, 'scripts', 'prefabs')
    if not os.path.isdir(prefab_dir):
        return None
    mods_dir = os.path.join(modroot, 'scripts', 'mods', modname)
    entries = []
    for f in sorted(os.listdir(prefab_dir)):
        if not f.endswith('.lua'):
            continue
        try:
            text = open(os.path.join(prefab_dir, f), encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        names = re.findall(r'Prefab\(\s*"([^"]+)"', text)
        anims = re.findall(r'Asset\(\s*"ANIM"\s*,\s*"([^"]+)"', text)
        for nm in names:
            anim = None
            for a in anims:
                base = os.path.basename(a)
                if base[:-4] == nm or base.startswith(nm) or nm.startswith(base[:-4]):
                    anim = a
                    break
            if anim is None and anims:
                anim = anims[0]
            if anim:
                if native:
                    # 纯原生模式：scripts/mods/<mod名>/ 死引用（owner 校验合法，手工 mod 格式）
                    target = 'scripts/mods/%s/%s' % (modname, anim)
                else:
                    target = 'scripts/mods/%s/%s' % (modname, anim)
                    # ★ 过滤：anim zip 必须真实存在于资源副本 scripts/mods/<modname>/ 下。
                    #   否则框架注册时 "Could not find an asset matching ... in any of the
                    #   search paths" → animation resource skipped（WARN）+ 白白占用
                    #   FW_EARLY_HOLDER 槽位。原版动画（如 anim/seeds.zip 等）AIP 包内没有，
                    #   应跳过让引擎按需从原版路径解析。
                    if not os.path.isfile(os.path.join(mods_dir, anim)):
                        continue
                entries.append((nm, target))
    if not entries:
        return None
    lines = ['-- Generated automatically.', 'return {']
    for nm, target in sorted(set(entries)):
        if native:
            # 手工适配 mod：不标 preload（趣味食物/英雄联盟武器验证格式）
            lines.append('    { name = "%s", anim = "%s" },' % (nm, target))
        else:
            # preload=true 是**死字段**（early.lua:399 收进 item.preload，全框架无读取点）；
            # 这里保留只为复现旧兼容层产物格式，动画真正生效靠条目本身。
            lines.append('    { name = "%s", anim = "%s", preload = true },' % (nm, target))
    lines.append('}')
    return '\r\n'.join(lines) + '\r\n'


def collect_all_assets(modroot):
    """扫描 modmain.lua + scripts/ 下全部 Lua 的静态 Asset("TYPE","path") 调用（跨行、去重保序）。

    用途：生成 Assets 全量声明模块（永不妥协 init/init_assets.lua 模式）。
    柠版引擎不收集 prefab 定义第三参数的 assets 表（PC 收集）；动画 build 必须
    通过 modmain 级 Assets = {...} 注册 → 大 mod 必须把全部 Asset 提升到 Assets 表。
    注意：动态拼接 Asset（"anim/"..name..".zip"）在此跳过，由 collect_anim_zips 用实际文件名补齐。
    """
    pat = re.compile(r'Asset\s*\(\s*["\']([A-Z_]+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)', re.S)
    assets, seen = [], set()
    targets = [os.path.join(modroot, 'modmain.lua')]
    scripts = os.path.join(modroot, 'scripts')
    if os.path.isdir(scripts):
        for r, dirs, files in os.walk(scripts):
            for f in files:
                if f.endswith('.lua'):
                    targets.append(os.path.join(r, f))
    for p in targets:
        if not os.path.isfile(p):
            continue
        try:
            t = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for m in pat.finditer(t):
            # 过滤注释：匹配起点前最近的非空白字符是 '-'（行注释内）
            head = t[max(0, m.start() - 40):m.start()].rstrip()
            if head.endswith('--') or re.search(r'--\s*$', head):
                continue
            key = (m.group(1), m.group(2))
            if key not in seen:
                seen.add(key)
                assets.append('Asset("%s","%s")' % key)
    return assets


def collect_anim_zips(modroot, assets):
    """扫描根 anim/ 全部 zip，把未被静态 Asset 覆盖的动画补为 Asset("ANIM",...)。

    覆盖动态拼接声明（Asset("ANIM","anim/"..name..".zip")，prefab 局部变量在
    Assets 模块内无定义，无法原样拷入）——用实际文件名静态展开，保证全部 build 注册。
    """
    anim_dir = os.path.join(modroot, 'anim')
    if not os.path.isdir(anim_dir):
        return assets
    covered = set()
    for a in assets:
        m = re.search(r'"ANIM"\s*,\s*"anim/([^"]+)"', a)
        if m:
            covered.add(m.group(1))
    zips = sorted(os.listdir(anim_dir))
    for zf in zips:
        if zf.endswith('.zip') and zf not in covered:
            assets.append('Asset("ANIM","anim/%s")' % zf)
    return assets


def gen_assets_auto(modroot, modname, modkey_name):
    """生成 scripts/<key>_assets_auto.lua：`Assets = { 全部 Asset(...) }`。

    永不妥协模式：modmain 里 `Assets={...}` 只声明少量，其余动画在 prefab 内且
    柠版不收集 → 全量 Assets 模块 modimport 到 modmain env 覆盖 → 原生引擎注册全部 build。
    """
    assets = collect_all_assets(modroot)
    assets = collect_anim_zips(modroot, assets)
    if not assets:
        return None
    lines = ['-- Generated automatically. Do not edit.',
             '-- 全量 Assets 声明（柠版 build 注册通道，永不妥协 init_assets 模式）',
             'Assets = {']
    for a in assets:
        lines.append(a + ',')
    lines.append('}')
    body = '\r\n'.join(lines) + '\r\n'
    out = os.path.join(modroot, 'scripts', '%s_assets_auto.lua' % modkey_name)
    write_new_lua(out, body)
    return out


def gen_preload_assets(modroot, modname, native=False):
    if native:
        # 纯原生模式：根目录真实文件，但路径值用 scripts/mods/<mod名>/ 前缀
        #（owner 校验合法 + 手工适配 mod 同款死引用格式，文件不存在无害）
        base = modroot
        prefix = 'scripts/mods/%s/' % modname
    else:
        base = os.path.join(modroot, 'scripts', 'mods', modname)
        if not os.path.isdir(base):
            return None
        prefix = 'scripts/mods/%s/' % modname
    items = []
    # 所有 images xml
    imgs = os.path.join(base, 'images')
    if os.path.isdir(imgs):
        for r, dirs, files in os.walk(imgs):
            for f in files:
                if f.endswith('.xml'):
                    rel = os.path.relpath(os.path.join(r, f), base).replace('\\', '/')
                    items.append(prefix + rel)
    # minimap 顶层目录（储藏室/千年狐/景熹等结构：<mod根>/minimap/*.xml，v1.6.1）
    mmdir = os.path.join(base, 'minimap')
    if os.path.isdir(mmdir):
        for r, dirs, files in os.walk(mmdir):
            for f in files:
                if f.endswith('.xml'):
                    rel = os.path.relpath(os.path.join(r, f), base).replace('\\', '/')
                    items.append(prefix + rel)
    # modicon（★ v1.6.7：只写 .xml —— 框架 lazy_atlas.lua 的清单只吃 .xml，
    #   .tex 行会被静默丢弃；原先同时写 modicon.tex = 白白多一条无效条目）
    for f in ('modicon.xml',):
        p = os.path.join(base, f)
        if os.path.exists(p):
            items.append(prefix + f)
    # anim zip（modmain Assets 里声明的 ANIM 也放进来，取全部 anim zip 的少量?）
    # preload 清单以 xml/tex 为主；anim 由 early_prefab/modmain Asset 承担
    if not items:
        return None
    lines = ['-- Generated automatically.', 'return {']
    for it in sorted(set(items)):
        lines.append('    "%s",' % it)
    lines.append('}')
    return '\r\n'.join(lines) + '\r\n'


def ensure_minimap_preload(modroot, modname):
    """确保所有 minimap 图集 xml 都在 preload_assets_auto.lua 清单（v1.6.1）。

    背景（更多料理斑点灌木 v3.40-3.44 实证）：AddMinimapAtlas 只注册图集元数据，
    纹理对象由 preload_assets_auto.lua 清单预加载创建（日志 holder=FW_STATIC_ATLAS_N）。
    自建/新增 minimap 图集若漏清单 → AddAtlas 注册成功但 tex 未加载 → 小地图图标
    紫白乱码占位（无 0x500、无 region 报错，难排查）。正常 mod（储藏室/千年狐等）
    的 preload 清单都显式含 minimap xml。

    本函数扫描 mod 内全部 minimap 图集目录（minimap/ + images 下含 minimap 的目录），
    与现有清单求并集写回（缺啥补啥，幂等；保持清单原 BOM/CRLF 风格）。
    """
    pre = os.path.join(modroot, 'preload_assets_auto.lua')
    if not os.path.exists(pre):
        return
    raw = open(pre, 'rb').read()
    txt = raw.decode('utf-8-sig')
    items = []
    # 已登记条目
    existing = set()
    import re as _re
    for m in _re.finditer(r'"([^"]+)"', txt):
        existing.add(m.group(1))
    # 扫描 minimap 图集目录
    prefix = 'scripts/mods/%s/' % modname
    cand_dirs = []
    for d0 in ('minimap',):
        d = os.path.join(modroot, d0)
        if os.path.isdir(d):
            cand_dirs.append(d)
    imgs = os.path.join(modroot, 'images')
    if os.path.isdir(imgs):
        for r, dirs, files in os.walk(imgs):
            if 'minimap' in os.path.basename(r).lower():
                cand_dirs.append(r)
    for d in cand_dirs:
        for r, dirs, files in os.walk(d):
            for f in files:
                if f.endswith('.xml'):
                    # 仅当同目录有同名 tex（图集对）才进清单
                    if os.path.exists(os.path.join(r, f[:-4] + '.tex')):
                        rel = os.path.relpath(os.path.join(r, f), modroot).replace('\\', '/')
                        items.append(prefix + rel)
    new_items = sorted(set(items) - existing)
    if not new_items:
        print('== minimap preload 补全: 无需补充（%d 个已在清单）' % len(items))
        return
    # 在 return { 表内追加：新条目插到结尾 } 之前（v1.6.1 修正——误插 } 后 = Lua 语法错误）
    body = txt.rstrip()
    if body.endswith('}'):
        body = body[:-1].rstrip()
    body += '\r\n' + ''.join('    "%s",\r\n' % it for it in new_items) + '}\r\n'
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    data = body.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n').encode('utf-8')
    if has_bom:
        data = b'\xef\xbb\xbf' + data
    open(pre, 'wb').write(data)
    print('== minimap preload 补全: 新增 %d 个（%s...）' % (len(new_items), new_items[0]))


def gen_sound_banks(modroot, modname):
    sound_dir = os.path.join(modroot, 'sound')
    if not os.path.isdir(sound_dir):
        return None
    fevs = sorted(f for f in os.listdir(sound_dir) if f.endswith('.fev'))
    fsbs = sorted(f for f in os.listdir(sound_dir) if f.endswith('.fsb'))
    if not fevs and not fsbs:
        return None
    pairs = []
    for fev in fevs:
        base = fev[:-4]
        fsb = base + '.fsb'
        if os.path.exists(os.path.join(sound_dir, fsb)):
            pairs.append((fev, fsb))
    total = 0
    for fev, fsb in pairs:
        total += os.path.getsize(os.path.join(sound_dir, fev)) + os.path.getsize(os.path.join(sound_dir, fsb))
    lines = ['-- Generated by dst_mobile_adapter.py; do not edit by hand.',
             'return {',
             '    version = 2,',
             '    modname = "%s",' % modname,
             '    total_bytes = %d,' % total,
             '    pairs = {']
    for fev, fsb in pairs:
        lines.append('        { fev = "scripts/mods/%s/sound/%s", fsb = "scripts/mods/%s/sound/%s" },' % (modname, fev, modname, fsb))
    lines.append('    },')
    lines.append('}')
    return '\r\n'.join(lines) + '\r\n'




def gen_tile_preload(modroot, modname):
    """levels/ 自定义地形/瓦片预加载清单（v1.4.26，荔只只物语手工版实证）。

    棱镜/永不妥协/荔只只物语手工版均有此文件（通用机制，§20.25）：
    柠版不自动扫描 levels/，带自定义 turf 的 mod 必须预加载，否则地面空白/紫块。
    格式：{ type = "IMAGE", path = "scripts/mods/<mod名>/levels/..." }（tex 贴图）
          { type = "FILE",  path = "scripts/mods/<mod名>/levels/..." }（xml 瓦片定义）
    编码：无 BOM + CRLF（同 sound_banks_auto.lua）。
    """
    levels_dir = os.path.join(modroot, 'levels')
    if not os.path.isdir(levels_dir):
        return None
    entries = []  # (type, path)
    for r, dirs, files in os.walk(levels_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(r, f), modroot).replace('\\', '/')
            if f.lower().endswith('.tex'):
                entries.append(('IMAGE', 'scripts/mods/%s/%s' % (modname, rel)))
            elif f.lower().endswith('.xml'):
                entries.append(('FILE', 'scripts/mods/%s/%s' % (modname, rel)))
    # v1.5.0: 手写 tile_preload_extra.lua 自动合并（§22.6-7，景熹家居包实证框架合并两份清单）
    extra_p = os.path.join(levels_dir, 'tile_preload_extra.lua')
    if os.path.isfile(extra_p):
        try:
            et = open(extra_p, encoding='utf-8', errors='replace').read()
            for em in re.finditer(r'type\s*=\s*["\x27](\w+)["\x27]\s*,\s*path\s*=\s*["\x27]([^"\x27]+)["\x27]', et):
                ty, path = em.group(1).upper(), em.group(2)
                if (ty, path) not in entries:
                    entries.append((ty, path))
        except Exception:
            pass
    if not entries:
        return None
    lines = ['-- Generated automatically.', 'return {']
    for ty, path in sorted(entries, key=lambda x: x[1]):
        lines.append('    { type = "%s", path = "%s" },' % (ty, path))
    lines.append('}')
    return '\r\n'.join(lines) + '\r\n'


def gen_test(modroot, modname, modkey_name, native=False):
    """生成 test.lua（★ v1.6.7：升级到 contract v3）。

    旧形态（v1.6.6 及以前）是**裸数组**，两个硬伤：
      ① 没有 `contract_version` / `steps` / `surface` → 框架 Contract:Validate 第一步
         就判「steps must be a table」，整个套件从未真正跑起来；`autotest_suite` 收得到
         名字但面板里点开是空的；
      ② 断言 `type(G.FW_LoadPrefabs) == "function"` 是**空检** —— 46 个稳定分发器由
         框架 Setup 时无条件 rawset 进 _G，模块被禁用也不删，故恒通过。
    本版：A 层看「调用返回值」（FW_DiagnoseFailures 返回字符串 = 框架活着），
    B 层才判 type()；compat 断言只在旧兼容层模式生成。
    """
    def q(s):
        return str(s).replace('\\', '\\\\').replace('"', '\\"')

    steps = [
        ('fw_api_live', 'framework api live', """\
            local G = _G
            local diag = G.rawget(G, "FW_DiagnoseFailures")
            if type(diag) ~= "function" then
                return false, "FW_DiagnoseFailures 缺失（框架未 Setup）"
            end
            local ok, res = G.pcall(diag)
            if not ok then return false, "FW_DiagnoseFailures 抛错: " .. tostring(res) end
            if type(res) ~= "string" then
                return false, "返回值不是字符串（框架模块可能未起来）: " .. type(res)
            end
            return true, "框架存活: " .. res"""),
        ('fw_registry', 'framework registry', """\
            local G = _G
            local r = G.rawget(G, "FW_LOAD_RESULTS")
            if type(r) ~= "table" then return false, "FW_LOAD_RESULTS 缺失（注册表未建立）" end
            return true, "FW_LOAD_RESULTS 就位\""""),
    ]
    if not native:
        steps.append(('compat_installed', 'compat installed', """\
            local compat = _G.rawget(_G, "%s")
            if type(compat) ~= "table" then return false, "compat missing" end
            if compat.installed ~= true then return false, "compat not finished" end
            return true, "compat installed\"""" % ('%s_MOBILE_COMPAT' % modkey_name.upper())))

    lines = [
        '-- %s —— 柠版自测契约（contract v3，由 dst_mobile_adapter.py 生成）' % modname,
        '-- AUTOTEST_SURFACE_BEGIN',
        'local AUTOTEST_SURFACE = {',
        '    entrypoints = { "modmain.lua" },',
        '    -- 本文件不申报 prefabs/recipes/buttons：surface 填错比不填更糟',
        '    -- （框架会逐项核对，缺少就报 missing）。确认真实注册项后手工补。',
        '}',
        '-- AUTOTEST_SURFACE_END',
        'local test = {',
        '    contract_version = 3,',
        '    surface = AUTOTEST_SURFACE,',
        '    name = "%s", mod = "%s",' % (q(modname), q(modname)),
        '    capabilities = { "smoke" },',
        '    features = {',
        '        { id = "framework", risk = "smoke", steps = { %s } },'
        % ', '.join('"%s"' % s[0] for s in steps),
        '    },',
        '    steps = {',
    ]
    for sid, desc, body in steps:
        raw = body.split('\n')
        ind = min((len(l) - len(l.lstrip())) for l in raw if l.strip()) if any(l.strip() for l in raw) else 0
        body = '\r\n'.join('            ' + ln[ind:] for ln in raw)
        lines += [
            '        {',
            '            id = "%s", kind = "assert", scope = "shared",' % sid,
            '            -- %s' % desc,
            '            fn = function(ctx)',
            body,
            '            end,',
            '        },',
        ]
    lines += ['    },', '}', 'return test', '']
    return '\r\n'.join(lines)


# ---------------------------------------------------------------------------
# 兼容层生成 + modmain 注入
# ---------------------------------------------------------------------------
def collect_replicas(modroot):
    """从 modmain/scripts 收集 AddReplicableComponent("xxx") 列表。"""
    out = []
    for base in ('modmain.lua', 'scripts', 'modservercreationmain.lua'):
        p = os.path.join(modroot, base) if not os.path.isabs(base) else base
        if os.path.isdir(p):
            for r, dirs, files in os.walk(p):
                for f in files:
                    if f.endswith('.lua'):
                        _scan(os.path.join(r, f), out)
        elif os.path.isfile(p):
            _scan(p, out)
    return out


def _scan(path, out):
    try:
        t = open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return
    for m in re.finditer(r'AddReplicableComponent\(\s*"([^"]+)"', t):
        if m.group(1) not in out:
            out.append(m.group(1))


COMPAT_TEMPLATE = '''-- ============================================================================
-- {modname} 柠版兼容层（手机端 DST FW_ 框架，自动生成）
-- 用法：modmain.lua 第一行 modimport("scripts/mobile_compat_{modkey}.lua")
--       全部 modimport 结束后调用 {UP}_MOBILE_COMPAT.FinishLoad()
-- 职责：
--   1. 自检柠版框架 FW_ API 是否齐全（打印到日志，方便排障）
--   2. 提供 RegisterFW() 供 modmain 在 Assets/PrefabFiles 声明后调用
--   3. 手机端接管 AddRecipe2 → FW_RegisterRecipe（保守：已有配方不抢，失败回退原生）
--   4. 记录 installed 状态供 test.lua 断言
-- ============================================================================

local G = GLOBAL
local compat = {{
    installed = false,
    api = {{}},
    modname = "{modname}",
    is_mobile = type(G.rawget(G, "IsMobile")) == "function" and G.IsMobile(),
}}

-- ① 框架 API 自检（一律 rawget：字段缺失时 strict 抛错而非返回 nil）
compat.api.resources = type(G.rawget(G, "FW_PreloadAssets")) == "function" and type(G.rawget(G, "FW_LoadPrefabs")) == "function"
compat.api.recipes   = type(G.rawget(G, "FW_RegisterRecipe")) == "function"
compat.api.replicas  = type(G.rawget(G, "FW_AddReplicableComponent")) == "function"
compat.api.lifecycle = type(G.rawget(G, "FW_DoTaskInTime")) == "function"
compat.api.touch     = type(G.rawget(G, "FW_BindWidgetTouch")) == "function"

-- ② 主注册函数：在 modmain 的 Assets/PrefabFiles 声明之后调用
--    assets / prefabfiles 由 modmain 传入（modmain 环境局部表）。
--    ★禁止用 G.Assets/G.PrefabFiles 读全局：modmain 的 Assets= 是环境局部变量，
--      strict.lua 的 __index 对 GLOBAL 未定义字段直接抛错（variable 'Assets' is not declared）
--      → MOD-LOAD-ERROR → modmain 中断 → 业务函数未定义 → 连锁报错。
function compat.RegisterFW(assets, prefabfiles)
    if not compat.is_mobile or not compat.api.resources then
        print("[{UP}_MOBILE] RegisterFW skipped (pc or framework missing)")
        return false
    end

    -- 参数兜底：modmain 未传时用 rawget 读 GLOBAL（nil 安全，不触发 strict）
    local assets_table = assets or G.rawget(G, "Assets")
    local prefabs_table = prefabfiles or G.rawget(G, "PrefabFiles")

    local preload_list = {{}}
    if type(assets_table) == "table" then
        for _, asset in ipairs(assets_table) do
            if type(asset) == "table" and asset.file then
                table.insert(preload_list, asset.file)
            end
        end
    end
    -- ★ 全量动画兜底预加载：modmain Assets 常只声明 UI/驱动类动画（AIP 仅 2 条），
    --   物品/装备/武器动画在 prefab 文件内声明，柠版框架不会自动收集 → 世界内
    --   物品/装备/武器动画全空白（背包图标走 images 不受影响）。
    --   这里把资源副本 anim/ 下全部 zip 硬编码注入（生成期收集，Lua 无法列目录）。
    local seen = {{}}
    for _, f in ipairs(preload_list) do seen[f] = true end
    for _, f in ipairs({{{anim_block}}}) do
        if not seen[f] then
            table.insert(preload_list, f)
            seen[f] = true
        end
    end
    if #preload_list > 0 then
        G.FW_PreloadAssets(compat.modname, preload_list)
        print("[{UP}_MOBILE] FW_PreloadAssets count=" .. tostring(#preload_list))
    end

    -- ★ 原生 PrefabFiles 优先（手工适配 mod 验证模式）：
    --   趣味食物/英雄联盟武器等正常 mod 无 FW_LoadPrefabs 调用——原生引擎读 modmain env
    --   的 PrefabFiles 注册预制物，并**原生收集 prefab 第三参数 assets 注册 build**。
    --   FW_LoadPrefabs 接管会破坏该收集链（世界内动画空白，图标正常）。
    --   仅当原生 PrefabFiles 为空时才用 FW_LoadPrefabs 兜底。
    if type(prefabs_table) == "table" and #prefabs_table > 0 then
        print("[{UP}_MOBILE] PrefabFiles 原生注册（引擎读 modmain env），跳过 FW_LoadPrefabs 接管")
    elseif type(G.FW_LoadPrefabs) == "function" then
        local ok, loaded = G.FW_LoadPrefabs(compat.modname, prefabs_table or {{}})
        print("[{UP}_MOBILE] FW_LoadPrefabs fallback ok=" .. tostring(ok) .. " loaded=" .. tostring(loaded))
    end

{replica_block}
    return true
end

-- ③ 收尾：全部 modimport 完成后调用
function compat.FinishLoad()
    compat.installed = true
    print("[{UP}_MOBILE] adapter_ready=true mobile=" .. tostring(compat.is_mobile))
end

-- ④ AddRecipe2 接管（手机端 + 框架有 FW_RegisterRecipe 时）
{recipe_block}
-- 暴露到全局，供 modmain / test.lua 使用
G.rawset(G, "{UP}_MOBILE_COMPAT", compat)

return compat
'''


def render_compat(modname, modkey_name, replicas, patch_recipes, anims=()):
    up = modkey_name.upper()
    rep_lines = []
    for r in replicas:
        rep_lines.append('        G.FW_AddReplicableComponent("%s")' % r)
    replica_block = '\n'.join(rep_lines) if rep_lines else '    -- （modmain 无 AddReplicableComponent 声明）'
    # 全量动画清单（生成期从资源副本 anim/ 收集；anim zip 名不含 {}，可安全走 .format）
    anim_block = ', '.join('"%s"' % a for a in sorted(anims)) if anims else '-- （无 anim 清单）'
    recipe_block = '''if compat.is_mobile and compat.api.recipes and G.rawget(G, "@UP@_ADAPTER_RECIPES_PATCHED") ~= true then
    -- ★ AddRecipe2 不在 GLOBAL 上（modmain 环境注入 API），G.rawget 判存在；
    --   柠版新版缺失时静默跳过接管，配方走 modmain 环境原生 AddRecipe2。
    local orig_AddRecipe2 = G.rawget(G, "AddRecipe2")
    if type(orig_AddRecipe2) == "function" then
        G.rawset(G, "AddRecipe2", function(name, ingredients, tech, config, filters, ...)
            local register = G.rawget(G, "FW_RegisterRecipe")
            if type(register) == "function" then
                local owners = G.rawget(G, "FW_RECIPE_OWNERS") or {}
                local all_recipes = G.rawget(G, "AllRecipes")
                if owners[name] == nil and all_recipes ~= nil and all_recipes[name] == nil then
                    local ok = register(compat.modname, {
                        name = name, ingredients = ingredients, tech = tech,
                        config = config, filters = filters,
                        register = orig_AddRecipe2, override = false,
                    })
                    if ok then
                        print("[@UP@_MOBILE] AddRecipe2 -> FW_RegisterRecipe: " .. tostring(name))
                        return ok
                    end
                end
            end
            return orig_AddRecipe2(name, ingredients, tech, config, filters, ...)
        end)
    end
    G.rawset(G, "@UP@_ADAPTER_RECIPES_PATCHED", true)
end'''
    recipe_block = recipe_block.replace('@UP@', up) if patch_recipes else '-- 配方接管已禁用（--no-recipes）'
    return COMPAT_TEMPLATE.format(modname=modname, modkey=modkey_name, UP=up,
                                  replica_block=replica_block, recipe_block=recipe_block,
                                  anim_block=anim_block)


def filter_needed_anims(modroot, assets):
    """过滤出真正需要提升到 modmain Assets 的 ANIM（--native 用）：

    ① 删：zip 文件不存在（原版动画引用，如 seeds/blow_dart——引擎从原版路径解析）；
    ② 删：PrefabFiles 表内 prefab 的"第 1 个 ANIM"（prefab 原生收集通道负责主 build，
       已验证：鱼刀主 zip 地面正常）；
    ③ 保留：swap 手持/装备/皮肤 zip、模板动态注册 prefab（不在 PrefabFiles，aip_dress
       间接 require 的 assets 原生不收集）、prefab 第 2+ 个 ANIM。
    目的：Assets 表条目压到引擎加载上限内（实测约前 256 条 ANIM 才加载，
       265 位的面具动画不加载 → 空白），保证补缺动画全部生效。
    """
    modroot = os.path.abspath(modroot)
    mm_path = os.path.join(modroot, 'modmain.lua')
    primary = set()
    if os.path.exists(mm_path):
        mm = open(mm_path, encoding='utf-8', errors='replace').read()
        m = re.search(r'PrefabFiles\s*=\s*\{', mm)
        if m:
            seg = mm[m.start():m.start() + 30000]
            depth = 0
            for i, ch in enumerate(seg):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        seg = seg[:i]
                        break
            prefab_names = set(re.findall(r'"([^"]+)"', seg))
            for pn in prefab_names:
                pf = os.path.join(modroot, 'scripts', 'prefabs', pn + '.lua')
                if not os.path.isfile(pf):
                    continue
                t = open(pf, encoding='utf-8', errors='replace').read()
                # 静态 ANIM 列表（按出现顺序）
                stat = re.findall(r'Asset\(\s*["\']ANIM["\']\s*,\s*["\']anim/([^"\']+)["\']\s*\)', t)
                # 动态拼接 Asset("ANIM","anim/"..xx..".zip")
                dyn = re.findall(r'Asset\(\s*["\']ANIM["\']\s*,\s*["\']anim/"\s*\.\.\s*[^)]*\.zip', t)
                if stat:
                    primary.add(stat[0])
                if not stat and dyn:
                    primary.add(pn + '.zip')  # 动态拼接常见模式：anim/<prefab名>.zip
                if os.path.isfile(os.path.join(modroot, 'anim', pn + '.zip')):
                    primary.add(pn + '.zip')
    keep = []
    dropped_static = 0
    for a in assets:
        m = re.search(r'"ANIM"\s*,\s*"([^"]+)"', a)
        if not m:
            continue
        zipname = os.path.basename(m.group(1))
        if not os.path.isfile(os.path.join(modroot, 'anim', zipname)):
            dropped_static += 1
            continue  # 原版引用
        if zipname in primary:
            continue  # prefab 通道负责
        keep.append(a)
    print('    Assets 过滤: 原版引用删 %d, prefab主动画删 %d, 保留补缺 %d 条'
          % (dropped_static, len(assets) - len(keep) - dropped_static, len(keep)))
    return keep


def inject_fw_preload(modroot, modname):
    """注入 FW_PreloadAssets 调用（纯原生 modmain 追加，柠版框架通道）：

    背景（AIP 第十三轮实证）：柠版引擎只加载 prefab 第 1 个 ANIM；modmain Assets
    表补缺（125 条，swap 在 27 位）实测无效；SetBuild/OverrideSymbol 不触发加载。
    → swap 手持/装备/皮肤 zip（第 2+ 个 ANIM）永远不加载 → 手持/穿戴/皮肤空白。
    唯一验证有效（棱镜/能力勋章）的通道是框架 FW_PreloadAssets：把全部 anim zip
    显式预加载 → build 全部注册 → OverrideSymbol/SetBuild 时 build 已在内存。

    注入块放在 modmain 末尾（_G=GLOBAL 之后），判存在跳过（PC 无 FW_ 不影响）。
    返回注入 zip 数。
    """
    path = os.path.join(modroot, 'modmain.lua')
    anim_dir = os.path.join(modroot, 'anim')
    if not os.path.exists(path) or not os.path.isdir(anim_dir):
        return 0
    zips = sorted(f for f in os.listdir(anim_dir) if f.lower().endswith('.zip'))
    if not zips:
        return 0
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig', errors='replace')
    if text.count('\r\n') >= text.count('\n') // 2:
        nl = '\r\n'
    else:
        nl = '\n'
    if 'FW_PreloadAssets' in text:
        return 0
    lines = ['', '-- 柠版 FW_ 动画预加载（框架通道；PC 无框架自动跳过）', 'do']
    lines.append('    local _fw = GLOBAL.rawget(GLOBAL, "FW_PreloadAssets")')
    lines.append('    if type(_fw) == "function" then')
    body = ['        _fw("%s", {' % modname.replace('"', '\\"')]
    for z in zips:
        body.append('            "anim/%s",' % z)
    body.append('        })')
    lines.extend(body)
    lines.extend(['    end', 'end', ''])
    block = nl.join(lines)
    text = text.rstrip() + nl + block
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))
    print('    FW_PreloadAssets 注入: %d 个 anim zip 预加载（modmain 末尾）' % len(zips))
    return len(zips)


def inject_assets_append(modroot, assets):
    """追加式 Assets 补全（native 纯原生模式专用）：

    把 collect_all_assets+collect_anim_zips 得到的全部 ANIM 提升进 modmain 的
    Assets={...} 表（保留原表，只补缺失项）。DST 原生引擎加载 mod 时必然加载
    Assets 表 → 全部 build（含 swap 手持/装备/皮肤）注册。
    背景：prefab 第三参数 assets 的原生收集在柠版对多 ANIM（第 2 个起）不可靠；
    模板动态注册的 prefab（aip_horse_head 等不在 PrefabFiles）完全不收集。
    只补 ANIM；ATLAS/IMAGE 由 prefab 收集（图标/地面正常已验证）。
    返回补入条数。幂等（已含的跳过）。
    """
    path = os.path.join(modroot, 'modmain.lua')
    if not os.path.exists(path):
        return 0
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig', errors='replace')
    crlf = text.count('\r\n') >= text.count('\n') // 2
    nl = '\r\n' if crlf else '\n'
    lines = text.splitlines()

    start = end = None
    for i, l in enumerate(lines):
        if re.match(r'\s*Assets\s*=\s*\{', l):
            start = i
            j = i
            depth = 0
            while j < len(lines):
                depth += lines[j].count('{') - lines[j].count('}')
                if depth <= 0:
                    end = j
                    break
                j += 1
            break
    existing = set()
    if start is not None and end is not None:
        for l in lines[start:end + 1]:
            m = re.search(r'Asset\(\s*"ANIM"\s*,\s*"([^"]+)"', l)
            if m:
                existing.add(m.group(1))
    need = []
    for a in assets:
        m = re.search(r'"ANIM"\s*,\s*"([^"]+)"', a)
        if m and m.group(1) not in existing:
            need.append(a)
    if not need:
        return 0
    if end is not None:
        indent = re.match(r'\s*', lines[end]).group(0)
        ins = [indent + a + ',' for a in need]
        lines[end:end] = ins
    else:
        # 无 Assets 表：在文件开头（_G 后）插入新表
        lines.insert(0, '-- 全量 ANIM Assets（柠版 build 注册通道，自动追加）')
        lines.insert(0, 'Assets={')
        for a in need:
            lines.insert(1, '    ' + a + ',')
        lines.insert(1, '}')
    text = nl.join(lines)
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))
    return len(need)


def inject_modmain(modroot, modname, modkey_name):
    """注入 modmain.lua：开头 import / RegisterFW / FinishLoad。幂等。返回注入点列表。"""
    path = os.path.join(modroot, 'modmain.lua')
    if not os.path.exists(path):
        return ['modmain.lua 不存在，跳过注入']
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig', errors='replace')
    crlf = text.count('\r\n') >= text.count('\n') // 2
    nl = '\r\n' if crlf else '\n'
    compat_path = 'scripts/mobile_compat_%s.lua' % modkey_name
    up = modkey_name.upper()
    done = []

    if 'mobile_compat_%s.lua' % modkey_name not in text:
        lines = text.splitlines()
        insert_at = 0
        # 跳过注释/空行/第一个 local _G=GLOBAL 之后
        for i, l in enumerate(lines):
            if l.strip().startswith('local _G=GLOBAL') or l.strip().startswith('local _G = GLOBAL'):
                insert_at = i + 1
                break
        lines.insert(insert_at, '')
        lines.insert(insert_at, '-- 柠版兼容层（手机端 FW_ 框架，PC 端自动跳过）')
        lines.insert(insert_at, 'modimport("%s")' % compat_path)
        text = nl.join(lines)
        done.append('开头注入 modimport')

    # ★ Assets 全量声明模块：modmain Assets 表结束后注入（覆盖为全量，原生引擎注册全部 build）
    assets_mod = 'scripts/%s_assets_auto.lua' % modkey_name
    if os.path.isfile(os.path.join(modroot, assets_mod)) and 'assets_auto.lua' not in text:
        lines = text.splitlines()
        pos = None
        for i, l in enumerate(lines):
            if re.match(r'\s*Assets\s*=\s*\{', l):
                j = i
                while j < len(lines) and not lines[j].strip().startswith('}'):
                    j += 1
                if j < len(lines):
                    pos = j + 1
                break
        if pos is None:
            pos = 0
        block = [
            '-- 全量 Assets（柠版 build 注册通道，永不妥协 init_assets 模式）',
            'modimport("%s")' % assets_mod,
            '',
        ]
        lines[pos:pos] = block
        text = nl.join(lines)
        done.append('注入全量 Assets 模块（%s）' % assets_mod)

    if 'RegisterFW' not in text:
        lines = text.splitlines()
        pos = None
        # 优先 PrefabFiles 赋值块结束后
        for i, l in enumerate(lines):
            if re.match(r'\s*PrefabFiles\s*=', l):
                j = i
                while j < len(lines) and not lines[j].strip().endswith('}'):
                    j += 1
                pos = j + 1
                break
        if pos is None:
            for i, l in enumerate(lines):
                if l.strip().startswith('modimport('):
                    pos = i
                    break
        if pos is None:
            pos = len(lines)
        block = [
            '',
            'local %s_compat = _G.rawget(_G, "%s_MOBILE_COMPAT")' % (modkey_name, up),
            'if type(%s_compat) == "table" and type(%s_compat.RegisterFW) == "function" then' % (modkey_name, modkey_name),
            '    %s_compat:RegisterFW(Assets, PrefabFiles)' % modkey_name,
            'end',
            '',
        ]
        lines[pos:pos] = block
        text = nl.join(lines)
        done.append('注入 RegisterFW（%s）' % ('PrefabFiles 块后' if re.search(r'\s*PrefabFiles\s*=', text) else '首个 modimport 前/文件末尾'))

    if 'FinishLoad' not in text:
        text = text.rstrip() + nl + nl + 'local %s_compat_finish = _G.rawget(_G, "%s_MOBILE_COMPAT")' % (modkey_name, up) + nl
        text += 'if type(%s_compat_finish) == "table" and type(%s_compat_finish.FinishLoad) == "function" then' % (modkey_name, modkey_name) + nl
        text += '    %s_compat_finish.FinishLoad()' % modkey_name + nl
        text += 'end' + nl
        done.append('末尾注入 FinishLoad')

    out = text.encode('utf-8')
    if bom:
        out = b'\xef\xbb\xbf' + out
    open(path, 'wb').write(out)
    return done


def write_new_lua(path, content):
    """新 .lua：UTF-8 BOM + CRLF。"""
    open(path, 'wb').write(b'\xef\xbb\xbf' + content.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8'))


# ---------------------------------------------------------------------------
# 柠版触摸滚动适配（--touch-scroll）
# AIP §20.15 三通道：OnTouchStart 系列（简易存储式）+ SetDragable（ScrollableList 式）
# ---------------------------------------------------------------------------
def find_scroll_classes(target):
    """扫描 scripts/widgets + scripts/screens 下自定义滚动类文件。

    特征：内容含 CONTROL_SCROLLBACK/CONTROL_SCROLLFWD（自绘滚动响应）、
    SetScrollBound / ScrollByPixels / SetScrollable 等滚动 API，且是 Class( 类定义。
    返回相对 scripts/ 的 require 路径（如 widgets/redux/aipScroller）。
    """
    rels = []
    base = os.path.join(target, 'scripts')
    if not os.path.isdir(base):
        return rels
    markers = ('CONTROL_SCROLLBACK', 'CONTROL_SCROLLFWD',
               'ScrollByPixels', 'SetScrollable')
    for r, dirs, files in os.walk(base):
        if 'mods' in r.split(os.sep):
            continue  # 跳过资源副本区
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                t = open(p, encoding='utf-8-sig', errors='replace').read()
            except Exception:
                continue
            if not any(m in t for m in markers):
                continue
            if 'Class(' not in t:
                continue
            rel = os.path.relpath(p, base).replace('\\', '/')[:-4]  # 去 .lua
            if rel not in rels:
                rels.append(rel)
    return rels


TOUCH_SCROLL_BLOCK = r'''
-- === 柠版触摸滚动适配（工具注入 --touch-scroll，AIP §20.15 三通道）===
do
    local __G = GLOBAL
    local __rels = %RELS%
    local function __ts_scroll(scroller, dy)
        if scroller.Offset then
            scroller:Offset(dy)
        elseif scroller.ScrollByPixels then
            scroller:ScrollByPixels(dy)
        elseif scroller.ScrollToOffset then
            scroller:ScrollToOffset(dy)
        elseif scroller.Scroll then
            -- ScrollableList 系: Scroll(步数), 像素→步换算
            local __st = (scroller.item_height or 0) + (scroller.item_padding or 0)
            scroller:Scroll((__st > 0) and (dy / __st) or (dy * 0.05))
        end
    end
    local function __ts_install(t, scroller)
        if t.__fw_ts_installed then return end
        t.__fw_ts_installed = true
        t._touch_id = nil
        t._touch_last_y = nil
        function t:OnTouchStart(id, x, y)
            if self._touch_id == nil then
                self._touch_id = id
                self._touch_last_y = y
                if __G.TheFrontEnd then __G.TheFrontEnd:LockFocus(true, id) end
                return true
            end
            return false
        end
        function t:OnTouchMove(id, x, y)
            if self._touch_id == id and self._touch_last_y ~= nil then
                local dy = y - self._touch_last_y
                self._touch_last_y = y
                if dy ~= 0 then __ts_scroll(scroller, dy) end
                return true
            end
            return false
        end
        function t:OnTouchEnd(id, x, y)
            if self._touch_id == id then
                self._touch_id = nil
                self._touch_last_y = nil
                if __G.TheFrontEnd then __G.TheFrontEnd:LockFocus(false, id) end
                return true
            end
            return false
        end
        function t:OnTouchCancel(id)
            if self._touch_id == id then
                self._touch_id = nil
                self._touch_last_y = nil
                if __G.TheFrontEnd then __G.TheFrontEnd:LockFocus(false, id) end
            end
        end
    end
    local function __ts_wrap(cls)
        if type(cls) ~= "table" or type(cls._ctor) ~= "function" then return end
        if cls.__fw_touch_scroll then return end
        cls.__fw_touch_scroll = true
        local __old = cls._ctor
        cls._ctor = function(self, ...)
            __old(self, ...)
            if type(self.EnableTouchScroll) == "function" then
                self:EnableTouchScroll()
            end
        end
        function cls:EnableTouchScroll()
            if self.touchScrollEnabled then return end
            self.touchScrollEnabled = true
            local scroller = self
            local black = self.black
            local tgt = black or self
            __ts_install(tgt, scroller)
            __ts_install(self, scroller)
            if type(tgt.SetDragable) == "function" then
                tgt:SetDragable(true)
                tgt:SetDragUpdateFn(function(x, y, dx, dy)
                    if dy ~= 0 then __ts_scroll(scroller, dy) end
                end)
            end
        end
    end
    for _, __rel in ipairs(__rels) do
        if type(__rel) == "string" then
            local __ok, __cls = pcall(require, __rel)
            if __ok then __ts_wrap(__cls) end
        end
    end
end
'''


def inject_touch_scroll(target):
    """扫描滚动类并在 modmain.lua 末尾注入柠版触摸滚动适配。返回注入的类数量。"""
    rels = find_scroll_classes(target)
    if not rels:
        return 0
    modmain = os.path.join(target, 'modmain.lua')
    if not os.path.exists(modmain):
        return 0
    raw = open(modmain, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig', errors='replace')
    if '__fw_touch_scroll' in text:
        return 0  # 已注入过
    rel_lua = '{ "%s" }' % '", "'.join(rels)
    block = TOUCH_SCROLL_BLOCK.replace('%RELS%', rel_lua)
    out = (text.rstrip() + '\n' + block + '\n').encode('utf-8')
    if bom:
        out = b'\xef\xbb\xbf' + out
    open(modmain, 'wb').write(out)
    return len(rels)


TOUCH_SCROLL_FILE_BLOCK = r'''
-- === 柠版触摸滚动适配（工具注入，AIP §20.15 三通道）===
local __G_TS = GLOBAL
function %CLASS%:EnableTouchScroll()
    if self.touchScrollEnabled then return end
    self.touchScrollEnabled = true
    local scroller = self
    local black = self.black
    -- 触摸通道必须挂双处：black（命中垫层）+ Scroller 自身（所有内容的祖先，
    -- 触摸分发必经）。只挂 black 时，可交互子项（如 Menu 的 ImageButton 菜单项）
    -- 消费触摸 → 事件不经过兄弟节点 black → 该区域无法滑动（AIP 书籍左菜单实测）。
    local function install_touch(t)
        if t == nil or t.__fw_ts_installed then return end
        t.__fw_ts_installed = true
        t._touch_id = nil
        t._touch_last_y = nil
        function t:OnTouchStart(id, x, y)
            if self._touch_id == nil then
                self._touch_id = id
                self._touch_last_y = y
                if __G_TS.TheFrontEnd then __G_TS.TheFrontEnd:LockFocus(true, id) end
                return true
            end
            return false
        end
        function t:OnTouchMove(id, x, y)
            if self._touch_id == id and self._touch_last_y ~= nil then
                local dy = y - self._touch_last_y
                self._touch_last_y = y
                if dy ~= 0 then
                    if scroller.Offset then scroller:Offset(dy)
                    elseif scroller.ScrollByPixels then scroller:ScrollByPixels(dy)
                    elseif scroller.ScrollToOffset then scroller:ScrollToOffset(dy)
                    elseif scroller.Scroll then
                        -- ScrollableList 系: Scroll(步数), 像素→步换算
                        local __st = (scroller.item_height or 0) + (scroller.item_padding or 0)
                        scroller:Scroll((__st > 0) and (dy / __st) or (dy * 0.05))
                    end
                end
                return true
            end
            return false
        end
        function t:OnTouchEnd(id, x, y)
            if self._touch_id == id then
                self._touch_id = nil
                self._touch_last_y = nil
                if __G_TS.TheFrontEnd then __G_TS.TheFrontEnd:LockFocus(false, id) end
                return true
            end
            return false
        end
        function t:OnTouchCancel(id)
            if self._touch_id == id then
                self._touch_id = nil
                self._touch_last_y = nil
                if __G_TS.TheFrontEnd then __G_TS.TheFrontEnd:LockFocus(false, id) end
            end
        end
    end
    install_touch(black)
    install_touch(self)
    if black ~= nil and type(black.SetDragable) == "function" then
        black:SetDragable(true)
        black:SetDragUpdateFn(function(x, y, dx, dy)
            if dy ~= 0 then
                if scroller.Offset then scroller:Offset(dy)
                elseif scroller.ScrollByPixels then scroller:ScrollByPixels(dy)
                elseif scroller.ScrollToOffset then scroller:ScrollToOffset(dy)
                elseif scroller.Scroll then
                    local __st = (scroller.item_height or 0) + (scroller.item_padding or 0)
                    scroller:Scroll((__st > 0) and (dy / __st) or (dy * 0.05))
                end
            end
        end)
    end
end
local __TS_OLD_CTOR = %CLASS%._ctor
%CLASS%._ctor = function(self, ...)
    __TS_OLD_CTOR(self, ...)
    if type(self.EnableTouchScroll) == "function" then self:EnableTouchScroll() end
end
'''


def inject_defensive_fixes(target):
    """★ 通用防御性修复注入（英雄联盟武器手工版 10 个 prefab/组件 nil 防护 +
    滚动条 lastx 崩溃的通用化，对所有 Mod 自动生效）：

    a) fx 特效变量判空：`fx.Transform:SetPosition(...)`（fx 来自 SpawnPrefab 可能 nil）
       单行/连续多行 → `if fx then ... end`。变量名命中 fx/effect/eff/spark/light/
       smoke/ring/blast/flash/wave 等特效词且文件内 local 创建过 → 候选；
       文件内已有 `if fx then/if fx and/if not fx` 判空模式 → 跳过（不重复包裹）。
    b) `if target:IsValid() then` → `if target and target:IsValid() then`（target 可能 nil）。
    c) 滚动条触屏崩溃（lastx nil）：`TheFrontEnd.lastx/lasty` 使用处加
       `(TheFrontEnd.lastx or self._drag_lastx or 0)` 兜底，并在 SetOnDown 回调
       注入 `self._drag_lastx/_drag_lasty` 记录按下点（手工版 pedia_scrollablelist 同款）。
       文件已含 `_drag_lasty`（手工重写/补丁覆盖）→ 跳过。

    返回 (fx 包裹数, target 判空数, lastx 替换数, SetOnDown 注入数,
    SpawnPrefab 链式判空数)。
    已修复文件（含 `if fx then`/`if target and`/`_drag_lasty`）全部自动跳过，幂等。"""
    FX_VAR = re.compile(r'^[a-z_][a-z0-9_]*(?:fx|effect|eff|spark|light|smoke|ring|blast|flash|wave)[a-z0-9_]*$')
    fx_n = target_n = lastx_n = setondown_n = items_n = sp_n = 0
    for r, dirs, files in os.walk(target):
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
                text = raw.decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            bom = raw.startswith(b'\xef\xbb\xbf')
            changed = False

            # --- a) fx 判空 ---
            if 'Transform:Set' in text:
                # 文件内已判空的变量集合（前文 if fx then / if fx and / if not fx）
                guarded = set(re.findall(r'if\s+(\w+)\s+then|if\s+(\w+)\s+and|if\s+not\s+(\w+)\s+', text))
                guarded = {g for gs in guarded for g in gs if g}
                created = set(re.findall(r'local\s+(\w+)\s*=', text))
                lines = text.split('\n')
                out_lines = []
                i = 0
                while i < len(lines):
                    line = lines[i]
                    m = re.match(r'^(\s*)(\w+)\.Transform:Set(Position|Rotation|Scale)\(([^()]*)\)\s*$', line)
                    if m and m.group(2) in created and m.group(2) not in guarded and FX_VAR.match(m.group(2)):
                        var = m.group(2)
                        # 收集连续同 var 的 Transform 单行
                        j = i
                        block = []
                        while j < len(lines):
                            mm = re.match(r'^(\s*)(\w+)\.Transform:Set(Position|Rotation|Scale)\(([^()]*)\)\s*$', lines[j])
                            if mm and mm.group(2) == var:
                                block.append(lines[j]); j += 1
                            else:
                                break
                        out_lines.append(re.match(r'\s*', line).group(0) + 'if %s then' % var)
                        out_lines.extend(block)
                        out_lines.append(re.match(r'\s*', line).group(0) + 'end')
                        fx_n += 1
                        changed = True
                        i = j
                        continue
                    out_lines.append(line)
                    i += 1
                text = '\n'.join(out_lines)

            # --- b) target:IsValid 判空 ---
            if re.search(r'if\s+(\w+):IsValid\(\)\s+then', text):
                def _tk(m):
                    return 'if %s and %s:IsValid() then' % (m.group(1), m.group(1))
                text, nsub = re.subn(r'if\s+(\w+):IsValid\(\)\s+then', _tk, text)
                if nsub:
                    target_n += nsub
                    changed = True

            # --- c) lastx/lasty 兜底（滚动条触屏崩溃）---
            if '_drag_lasty' not in text and ('TheFrontEnd.lasty' in text or 'TheFrontEnd.lastx' in text):
                # c1) 使用处兜底
                def _lx(m):
                    return '(TheFrontEnd.%s or self._drag_%s or 0)' % (m.group(1), m.group(1))
                text, n1 = re.subn(r'TheFrontEnd\.(lastx|lasty)', _lx, text)
                lastx_n += n1
                if n1:
                    changed = True
                # c2) SetOnDown 回调注入按下点记录（找最近 function( 体）
                m2 = re.search(r'(?:\.SetOnDown|:SetOnDown)\s*\(\s*function\([^)]*\)\s*', text)
                if m2:
                    ins = ('\n    self._drag_lastx = TheFrontEnd.lastx or 0\n'
                           '    self._drag_lasty = TheFrontEnd.lasty or 0\n')
                    text = text[:m2.end()] + ins + text[m2.end():]
                    setondown_n += 1
                    changed = True

            # --- d) items 越界 SetFocus 判空（触摸滑动到边界时 view_offset 越界 → nil，
            #       LOL pedia_scrollablelist.lua:345/348 实证：
            #       self.items[self.view_offset+1]:SetFocus() → attempt to index a nil value）---
            if 'self.items[' in text and 'SetFocus()' in text:
                def _sf(m):
                    expr = m.group(1).strip()
                    if 'view_offset' not in expr:
                        return m.group(0)
                    return ('if self.items[%s] then self.items[%s]:SetFocus() end'
                            % (expr, expr))
                text, n4 = re.subn(r'self\.items\[([^\]\n]+)\]:SetFocus\(\)', _sf, text)
                if n4:
                    items_n += n4
                    changed = True

            # --- e) SpawnPrefab 链式调用判空（v1.5.2：Forge 专属 prefab 缺失→SpawnPrefab
            #       返回 nil→立即 `.Transform` 索引崩溃；心之钢 lavaarena_firebomb_explosion
            #       实证。仅处理行首即 `SpawnPrefab('x').Method...` 单行链式调用，拆两行 +
            #       `if __sp then ... end`；注释/已有判空/赋值型跳过，__sp 幂等）---
            if 'SpawnPrefab(' in text:
                lines = text.split('\n')
                out_lines = []
                j = 0
                while j < len(lines):
                    line = lines[j]
                    sm = re.match(r'^(\s*)(SpawnPrefab\(\s*[\'\"][^\'\"]+[\'\"]\s*\))[.:]\s*([A-Za-z_]\w*)', line)
                    if sm and not line.lstrip().startswith('--'):
                        indent, call = sm.group(1), sm.group(2)
                        rest = line.strip()[len(call):]
                        out_lines.append(indent + 'local __sp = ' + call)
                        out_lines.append(indent + 'if __sp then __sp' + rest + ' end')
                        sp_n += 1
                        changed = True
                        j += 1
                        continue
                    out_lines.append(line)
                    j += 1
                text = '\n'.join(out_lines)

            if changed:
                out = text.encode('utf-8')
                if bom:
                    out = b'\xef\xbb\xbf' + out
                open(p, 'wb').write(out)
    return fx_n, target_n, lastx_n, setondown_n, items_n, sp_n


def cn_label(var):
    """把 post-construct 变量名映射为中文按钮名（找不到关键词返回 None → 用英文）。
    通用规则：命中常见英文功能词即用中文，柠版按钮栏显示中文（如 lol_wp_pedia→图鉴）。"""
    v = (' ' + var + ' ').lower()
    for kw, cn in (
            ('pedia', '图鉴'), ('book', '图鉴'), ('encyclopedia', '图鉴'), ('tome', '图鉴'),
            ('attri', '属性'), ('attribute', '属性'), ('status', '属性'), ('stat', '属性'),
            ('shop', '商店'), ('store', '商店'), ('market', '商店'), ('trade', '商店'),
            ('bag', '背包'), ('inventory', '背包'), ('backpack', '背包'),
            ('equip', '装备'),
            ('config', '设置'), ('setting', '设置'), ('option', '设置'),
            ('craft', '制作'), ('recipe', '制作'), ('cook', '烹饪'),
            ('skill', '技能'), ('talent', '技能'),
            ('quest', '任务'), ('task', '任务'), ('mission', '任务'),
            ('achieve', '成就'), ('achievement', '成就'),
            ('mail', '邮件'), ('letter', '信件'),
            ('map', '地图'), ('minimap', '地图'),
            ('menu', '菜单'), ('panel', '面板'), ('ui', '面板'),
            ('pet', '宠物'), ('mount', '坐骑'),
            ('talent', '天赋'), ('growth', '成长'),
            ('almanac', '图鉴'), ('collection', '图鉴'),
            ('dress', '装扮'), ('wardrobe', '衣柜'),
            ('storage', '存储'), ('bank', '存储'),
            ('buff', '状态'), ('debuff', '状态'),
            ('weather', '天气'), ('time', '时间'),
    ):
        if kw in v:
            return cn
    return None


def inject_mod_buttons(target, modname, character=''):
    """★ 通用柠版按钮注册（英雄联盟武器手工版按钮适配的通用化）：
    扫描 `AddClassPostConstruct('screens/playerhud', ...)` 中 `self.<var> = self:AddChild(<自定义widget>())`
    的面板型 widget（非 ImageButton/Text 等内置类）→ 自动注入 FW_RegisterModButton 注册，
    onpress = 面板 shown 互切（与手工版 lol_wp_attri/lol_wp_pedia 按钮同构）。

    PC 版固定坐标 logo 按钮在触屏不可点 → 柠版按钮栏按钮。按钮语义（开面板）由
    widget 的 Show/Hide 通用化，无需理解每个 mod 的按钮逻辑。返回注册数。

    增强（英雄联盟武器三 bug 通用化，LOL v6 验证）：
    - icon 提取：post-construct 内 `self.<var>_logo = self:AddChild(ImageButton('atlas','tex',...))`
      → 柠版按钮带 icon（原版按钮样式应用）
    - 原版按钮隐藏：`self.<var>_logo:Hide()` 注入（-- __fw_logo_hide 幂等）
    - 面板类内互切按钮归一：widget 文件内 `self.logo` + `self.back` SetOnClick 体含
      `self.logo:Show()`（PC 原版 back/logo 互切结构）→ back 点击改为直接 `self:Hide()`
      （-- __fw_back_hide 幂等），避免柠版按钮 shown toggle 与 back 逻辑冲突"""
    BUILTIN_WIDGETS = {
        'ImageButton', 'Button', 'Image', 'Text', 'Menu', 'Grid', 'ScrollingGrid',
        'ScrollableList', 'Frame', 'Panel', 'AnimButton', 'ImageNineGrid',
        'InventoryBar', 'ItemTile', 'ImageList', 'GridList', 'NumericSpinner',
        'Spinner', 'CheckBox', 'Slider', 'ScrollBar', 'TabGroup', 'ListWidget',
        'FlowWidget', 'RowWidget', 'ColumnWidget', 'ButtonWidget', 'Label',
        'ImageTextButton', 'Tooltip', 'WorldMap', 'Minimap', 'HealthBar',
        'PopupDialogScreen', 'Screen', 'Widget', 'TextButton', 'ImageWidget',
        'ScrollableListPanel', 'GenericList', 'PlainText', 'CraftingMenuGrid',
    }
    n = 0
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
                text = raw.decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            if "AddClassPostConstruct('screens/playerhud'" not in text \
                    and 'AddClassPostConstruct("screens/playerhud"' not in text:
                continue
            if 'FW_RegisterModButton' in text:
                continue  # 已注册（幂等）
            # 找 post-construct 块内 AddChild 的面板型 widget
            found = []
            for m in re.finditer(r"self\.(\w+)\s*=\s*self:AddChild\((\w+)\(\)\)", text):
                var, cls = m.group(1), m.group(2)
                if cls in BUILTIN_WIDGETS:
                    continue
                if cls == var:  # 同名不可靠，仍需注册（类=var 常见）
                    pass
                found.append((var, cls))
            if not found:
                continue
            # --- 增强1: post-construct 内 `self.<var>_logo` 原版按钮 → 提取 icon/pos/scale + 注入隐藏
            logo_inject = []
            icons = {}
            extra_pos = {}
            for var, cls in found:
                logo_re = re.compile(
                    r"self\.%s_logo\s*=\s*self:AddChild\(\s*ImageButton\(\s*'([^']+)'\s*,\s*'([^']+)'" % re.escape(var))
                lm = logo_re.search(text)
                if lm:
                    icons[var] = [lm.group(1), lm.group(2)]
                    pm = re.search(r"self\.%s_logo:SetPosition\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)" % re.escape(var), text)
                    sm = re.search(r"self\.%s_logo:SetScale\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)" % re.escape(var), text)
                    if pm and sm:
                        extra_pos[var] = (pm.group(1), pm.group(2), sm.group(1))
                    mark = '-- __fw_logo_hide'
                    if mark not in text:
                        logo_inject.append(
                            '    -- %s: 原版固定按钮已由柠版按钮替代(样式经 icon 转移)\n'
                            '    self.%s_logo:Hide()' % (mark, var))
            # --- 增强2a: 面板类内 `self.logo` → 提取 icon（widget 文件，back/logo 互切结构）
            wfiles = {}
            for var, cls in found:
                if var in icons:
                    continue
                mreq = re.search(
                    r"require\s*\(\s*['\"]([^'\"]*/widgets/%s)['\"]\s*\)" % re.escape(cls), text)
                if not mreq:
                    mreq = re.search(
                        r"require\s+['\"]([^'\"]*/widgets/%s)['\"]" % re.escape(cls), text)
                if not mreq:
                    continue
                wpath = os.path.normpath(os.path.join(target, 'scripts', mreq.group(1) + '.lua'))
                if not os.path.isfile(wpath):
                    continue
                try:
                    wraw = open(wpath, 'rb').read()
                    wtxt = wraw.decode('utf-8-sig', errors='replace')
                except Exception:
                    continue
                wfiles[cls] = (wpath, wraw, wtxt)
                lm = re.search(r"self\.logo\s*=\s*self:AddChild\(\s*ImageButton\(\s*'([^']+)'\s*,\s*'([^']+)'", wtxt)
                if lm:
                    icons[var] = [lm.group(1), lm.group(2)]
            blocks = []
            for var, cls in found:
                key = var.upper() + '_OPEN'
                label = cn_label(var) or ' '.join(w.capitalize() for w in var.replace('_', ' ').split())
                icon_field = ''
                if var in icons:
                    icon_field = '        icon = { "%s", "%s" },\n' % (icons[var][0], icons[var][1])
                pos_field = ''
                if var in extra_pos:
                    pos_field = ('        pos = { x = %s, y = %s },\n'
                                 '        scale = %s,\n' % (extra_pos[var][0], extra_pos[var][1], extra_pos[var][2]))
                char_field = ('        character = "%s",\n' % character) if character else ''
                blocks.append(
                    "if type(GLOBAL.FW_RegisterModButton) == \"function\" then\n"
                    "    GLOBAL.FW_RegisterModButton(%s, {\n"
                    "        key = \"%s\",\n"
                    "        label = \"%s\",\n"
                    "%s%s%s"
                    "        visible = function(player)\n"
                    "            return player ~= nil and player.HUD ~= nil and player.HUD.%s ~= nil\n"
                    "        end,\n"
                    "        show_in_edit_mode = true,\n"
                    "        onpress = function()\n"
                    "            local ui = GLOBAL.ThePlayer and GLOBAL.ThePlayer.HUD and GLOBAL.ThePlayer.HUD.%s\n"
                    "            if ui then\n"
                    "                if ui.shown then ui:Hide() else ui:Show() end\n"
                    "            end\n"
                    "        end,\n"
                    "    })\n"
                    "end" % (repr(modname), key, label, icon_field, pos_field, char_field, var, var))
            inject = ('\n\n-- 柠版适配: PC 固定坐标按钮/面板 → 柠版 HUD 按钮（FW_RegisterModButton 通用注册）\n'
                      + '\n'.join(blocks))
            text = text.rstrip() + '\n' + inject + '\n'
            # --- 增强1b: logo 隐藏必须紧跟 logo 创建行之后（self 可用、且非 nil）。
            # 教训链: ①追加文件末尾顶层 → `self` 全局 nil 卡加载（v10 实证）；
            # ②深度平衡找块闭合 → 误插到 elseif 子块且早于 logo 创建 → nil（v11 实证）。
            # 正确落点 = `self.<var>_logo = self:AddChild(` 行尾之后，块内且创建后。
            if logo_inject:
                for entry in logo_inject:
                    vm = re.search(r"self\.(\w+)_logo:Hide\(\)", entry)
                    if not vm:
                        continue
                    var = vm.group(1)
                    anchor = re.search(
                        r"self\.%s_logo\s*=\s*self:AddChild\(" % re.escape(var), text)
                    if not anchor:
                        continue
                    nl = text.find('\n', anchor.end())
                    if nl < 0:
                        continue
                    logo_text = ('\n    -- 柠版适配: 原版固定 logo 按钮清除/隐藏（样式已转移到柠版按钮 icon）\n'
                                 + entry + '\n')
                    text = text[:nl + 1] + logo_text + text[nl + 1:]
            # --- 增强2b: 面板类内 back/logo 互切归一（widget 文件）
            for cls, (wpath, wraw, wtxt) in wfiles.items():
                if '__fw_back_hide' in wtxt:
                    continue
                if not re.search(r"self\.logo\s*=\s*self:AddChild\(\s*ImageButton\(", wtxt):
                    continue
                bm = re.search(r"self\.back\s*:\s*SetOnClick\s*\(\s*function\s*\(\)", wtxt)
                if not bm:
                    continue
                # 块平衡: 找 SetOnClick(function() ... end) 的闭合 end
                body_start = wtxt.find('function', bm.start())
                if body_start < 0:
                    continue
                depth = 1
                i = body_start + len('function') + 1
                j = wtxt.find('end', i)
                while j >= 0:
                    depth -= 1
                    if depth <= 0:
                        break
                    i = j + 3
                    j = wtxt.find('end', i)
                if j < 0:
                    continue
                # 检查体内是否含 self.logo:Show()（互切结构）
                inner = wtxt[bm.end():j]
                if 'self.logo:Show()' not in inner and 'self.logo:Show' not in inner:
                    continue
                new_body = '\n            -- __fw_back_hide: 原版 back/logo 互切改为直接关闭面板(柠版按钮统一开关)\n            self:Hide()\n        '
                # 保留原闭合 `end)`（j 指向 end 的 e；v1.4.1 曾用 j+3 跳过 end 只剩 `)`
                # → `unexpected symbol near ')'` 语法错误（attri:111 实证）
                wtxt = wtxt[:bm.end()] + new_body + wtxt[j:]
                out = wtxt.encode('utf-8')
                if wraw.startswith(b'\xef\xbb\xbf'):
                    out = b'\xef\xbb\xbf' + out
                open(wpath, 'wb').write(out)
                print('   - [按钮归一] %s: back SetOnClick → self:Hide()' % os.path.relpath(wpath, target))
            out = text.encode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf'):
                out = b'\xef\xbb\xbf' + out
            open(p, 'wb').write(out)
            n += len(found)
    return n


def key_btn_label(expr):
    """按键表达式 → 按钮文字。KEY_R→'R 键'；SKILLKEY→'技能'；RELOADKEY→'换弹'。"""
    k = expr.strip().split('.')[-1].strip().strip('"\'')
    k = re.sub(r'^KEY_', '', k)
    if k in ('SKILLKEY', 'SKILL', 'SKILL_KEY'):
        return '技能'
    if k in ('RELOADKEY', 'RELOAD', 'RELOAD_KEY'):
        return '换弹'
    if k in ('ATTACKKEY', 'ATTACK', 'ATTACK_KEY'):
        return '攻击'
    if len(k) == 1:
        return k + ' 键'
    if k and k != expr.strip():
        return k + ' 键'
    return '技能'


def find_character(target):
    """扫描 lua 找角色 prefab（FW_RegisterModButton/FW_RegisterCharacter 防跨角色泄漏用）：
    AddModCharacter("prefab") / FW_RegisterCharacter 的 prefab 字段 / MODCHARACTERLIST。
    返回第一个角色名或空串。"""
    cands = []
    pats = [
        re.compile(r'AddModCharacter\s*\(\s*["\x27]([A-Za-z_]\w*)["\x27]'),
        re.compile(r'FW_RegisterCharacter\s*\([^,]+,\s*\{\s*prefab\s*=\s*["\x27]([A-Za-z_]\w*)["\x27]'),
        re.compile(r'MODCHARACTERLIST\s*=\s*\{[^}]*?["\x27]([A-Za-z_]\w*)["\x27]'),
    ]
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            try:
                t = open(os.path.join(r, f), 'rb').read().decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            for pat in pats:
                for m in pat.finditer(t):
                    c = m.group(1)
                    if c not in cands:
                        cands.append(c)
    return cands[0] if cands else ''


def inject_lifecycle_tasks(target, modname):
    """★ 生命周期任务重写（v1.5.0，§20.27 实施）：
    扫描 `X:DoTaskInTime(delay, fn)` / `X:DoPeriodicTask(interval, fn)` 且任务变量被
    `task:Cancel()` 取消的**成对生命周期模式** → 替换为 __FW_LIFE_TASK / __FW_LIFE_PERIOD /
    __FW_LIFE_CANCEL（FW_DoTaskInTime/FW_DoPeriodicTask/FW_CancelLifecycle 可用时框架托管，
    pcall 失败回退原生 inst:DoTaskInTime/DoPeriodicTask/task:Cancel）。taskid 按文件去重命名。
    仅替换有 Cancel 配对的任务，避免破坏一次性任务语义。返回替换文件数。"""
    modmain_p = os.path.join(target, 'modmain.lua')
    if not os.path.isfile(modmain_p):
        return 0
    raw = open(modmain_p, 'rb').read()
    mm = raw.decode('utf-8-sig', errors='replace')
    if '__FW_LIFE_TASK' not in mm:
        helper = (
            '\n\n-- 柠版生命周期任务兼容垫片（__FW_LIFE_TASK/__FW_LIFE_PERIOD/__FW_LIFE_CANCEL，v1.5.0 工具注入）\n'
            '-- FW_DoTaskInTime/FW_DoPeriodicTask/FW_CancelLifecycle 可用 → 框架生命周期托管（断线/实体销毁自动清理）；\n'
            '-- 不可用 → pcall 回退原生 inst:DoTaskInTime/DoPeriodicTask/task:Cancel，不改变原语义。\n'
            'if GLOBAL.rawget(GLOBAL, "__FW_LIFE_TASK") == nil then\n'
            '    function GLOBAL.__FW_LIFE_TASK(inst, taskid, mname, delay, fn)\n'
            '        local fw = GLOBAL.rawget(GLOBAL, "FW_DoTaskInTime")\n'
            '        if type(fw) == "function" then\n'
            '            local ok, t = GLOBAL.pcall(fw, mname, inst, taskid, delay, fn)\n'
            '            if ok and t then return t end\n'
            '        end\n'
            '        return inst:DoTaskInTime(delay, fn)\n'
            '    end\n'
            '    function GLOBAL.__FW_LIFE_PERIOD(inst, taskid, mname, interval, fn, init)\n'
            '        local fw = GLOBAL.rawget(GLOBAL, "FW_DoPeriodicTask")\n'
            '        if type(fw) == "function" then\n'
            '            local ok, t = GLOBAL.pcall(fw, mname, inst, taskid, interval, fn, init or 0)\n'
            '            if ok and t then return t end\n'
            '        end\n'
            '        return inst:DoPeriodicTask(interval, fn, init or 0)\n'
            '    end\n'
            '    function GLOBAL.__FW_LIFE_CANCEL(inst, taskid, mname, native_cancel)\n'
            '        local c = GLOBAL.rawget(GLOBAL, "FW_CancelLifecycle")\n'
            '        if type(c) == "function" then GLOBAL.pcall(c, mname, inst, taskid) end\n'
            '        if type(native_cancel) == "function" then GLOBAL.pcall(native_cancel) end\n'
            '    end\n'
            'end')
        mm = mm.rstrip() + helper + '\n'
        out = mm.encode('utf-8')
        if raw.startswith(b'\\xef\\xbb\\xbf'):
            out = b'\\xef\\xbb\\xbf' + out
        open(modmain_p, 'wb').write(out)

    n = 0
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua') or f == 'modmain.lua':
                continue
            p = os.path.join(r, f)
            try:
                raw2 = open(p, 'rb').read()
            except Exception:
                continue
            t2 = raw2.decode('utf-8-sig', errors='replace')
            if '__FW_LIFE_TASK' in t2:
                continue  # 幂等：已重写
            # 收集任务赋值：local var = <expr>:DoTaskInTime(delay, ...) / DoPeriodicTask
            tasks = {}  # var -> (expr, kind)
            for m in re.finditer(
                    r'(?m)^\s*(?:local\s+)?([A-Za-z_]\w*)\s*=\s*([\w.\[\]"\x27]+)\s*:\s*(DoTaskInTime|DoPeriodicTask)\s*\(',
                    t2):
                var, expr, kind = m.group(1), m.group(2), m.group(3)
                if var not in tasks:
                    tasks[var] = (expr, kind)
            if not tasks:
                continue
            changed = False
            fbase = os.path.splitext(f)[0].replace('.', '_')
            # 有 Cancel 配对的任务才重写（一次性任务保持原生）；赋值替换用完整表达式串（无子串风险）
            paired = {}
            for i, (var, (expr, kind)) in enumerate(tasks.items()):
                if re.search(r'\b%s\s*:\s*Cancel\s*\(' % re.escape(var), t2):
                    paired[var] = (expr, kind, 'fwtask_%s_%d' % (fbase, i + 1))
            if not paired:
                continue
            for var, (expr, kind, tid) in paired.items():
                lname = 'TASK' if kind == 'DoTaskInTime' else 'PERIOD'
                old_a = '%s = %s:%s(' % (var, expr, kind)
                new_a = '%s = GLOBAL.__FW_LIFE_%s(%s, "%s", "%s", ' % (var, lname, expr, tid, modname)
                if old_a in t2:
                    t2 = t2.replace(old_a, new_a, 1)
                    changed = True
            # Cancel 替换：词边界回调式（防 task 误伤 ptask 子串；re.sub 单次扫描结果不重扫）
            cancel_map = {var: (expr, tid) for var, (expr, kind, tid) in paired.items()}

            def _cb(m):
                var = m.group(1)
                pair = cancel_map.get(var)
                if not pair:
                    return m.group(0)
                expr, tid = pair
                return 'GLOBAL.__FW_LIFE_CANCEL(%s, "%s", "%s", function() %s:Cancel() end)' % (expr, tid, modname, var)
            t2, nc = re.subn(r'\b([A-Za-z_]\w*)\s*:\s*Cancel\s*\(\)', _cb, t2)
            if nc:
                changed = True
            if changed:
                out = t2.encode('utf-8')
                if raw2.startswith(b'\\xef\\xbb\\xbf'):
                    out = b'\\xef\\xbb\\xbf' + out
                open(p, 'wb').write(out)
                n += 1
    return n


def inject_touch_pipeline(target, modname):
    """★ 触摸管线兼容注入（v1.5.0，§20.28 实施）：
    modmain 注入防误触层级 helper __FW_TOUCH_GUARD(x,y)（IsPaused→HasInputFocus→HasActiveItem→
    IsMapScreenOpen→placer→IsVirtualStickTouched→IsHudPoint→FW_IsActionButtonPoint）与
    __FW_TOUCH_ENTITIES(x,y)（TheSim:GetEntitiesAtScreenPoint 包装）；
    playercontroller 缺 OnTouchLong/OnGesture 时补默认（不消费，只挡 nil）。
    幂等 __FW_TOUCH_GUARD。返回 1 注入 / 0 跳过。"""
    modmain_p = os.path.join(target, 'modmain.lua')
    if not os.path.isfile(modmain_p):
        return 0
    raw = open(modmain_p, 'rb').read()
    mm = raw.decode('utf-8-sig', errors='replace')
    if '__FW_TOUCH_GUARD' in mm:
        return 0  # 幂等
    block = (
        '\n\n-- 柠版触摸管线兼容（__FW_TOUCH_GUARD/__FW_TOUCH_ENTITIES + OnTouchLong/OnGesture 补全，v1.5.0 工具注入）\n'
        '-- 自定义触摸处理（OnTouchStart/End hook、TheInput:AddTouch*Handler）可直接调用防误触/屏幕拾取 helper；\n'
        '-- 框架已有 OnTouchLong/OnGesture 时不覆盖（只补 nil）。\n'
        'if GLOBAL.rawget(GLOBAL, "__FW_TOUCH_GUARD") == nil then\n'
        '    function GLOBAL.__FW_TOUCH_GUARD(x, y)\n'
        '        if GLOBAL.ThePlayer == nil or GLOBAL.ThePlayer.components == nil then return false end\n'
        '        local pc = GLOBAL.ThePlayer.components.playercontroller\n'
        '        if pc == nil then return false end\n'
        '        if GLOBAL.TheFrontEnd ~= nil and GLOBAL.TheFrontEnd:HasInputFocus() then return false end\n'
        '        if pc.IsPaused ~= nil and pc:IsPaused() then return false end\n'
        '        if pc.HasActiveItem ~= nil and pc:HasActiveItem() then return false end\n'
        '        if pc.IsMapScreenOpen ~= nil and pc:IsMapScreenOpen() then return false end\n'
        '        if pc.IsVirtualStickTouched ~= nil and pc:IsVirtualStickTouched() then return false end\n'
        '        local apb = GLOBAL.rawget(GLOBAL, "FW_IsActionButtonPoint")\n'
        '        if type(apb) == "function" then\n'
        '            local ok, hit = GLOBAL.pcall(apb, x, y)\n'
        '            if ok and hit == true then return false end\n'
        '        end\n'
        '        return true\n'
        '    end\n'
        '    function GLOBAL.__FW_TOUCH_ENTITIES(x, y)\n'
        '        local gs = GLOBAL.TheSim and GLOBAL.TheSim.GetEntitiesAtScreenPoint\n'
        '        if type(gs) == "function" then\n'
        '            local ok, ents = GLOBAL.pcall(gs, GLOBAL.TheSim, x, y)\n'
        '            if ok and type(ents) == "table" then return ents end\n'
        '        end\n'
        '        return {}\n'
        '    end\n'
        'end\n'
        'AddComponentPostInit("playercontroller", function(controller)\n'
        '    if controller.OnTouchLong == nil then\n'
        '        controller.OnTouchLong = function(self, id) return false end\n'
        '    end\n'
        '    if controller.OnGesture == nil then\n'
        '        controller.OnGesture = function(self, theta, dist, state) end\n'
        '    end\n'
        'end)')
    mm = mm.rstrip() + block + '\n'
    out = mm.encode('utf-8')
    if raw.startswith(b'\\xef\\xbb\\xbf'):
        out = b'\\xef\\xbb\\xbf' + out
    open(modmain_p, 'wb').write(out)
    return 1


def gen_atlas_index(target, modname):
    """★ 生成 mod 图集索引（v1.6.1）：把 preload_assets_auto.lua 里的 ATLAS 资源路径
    落成 scripts/tr_atlas_index_auto.lua，供 __TR_FIND_ATLAS 反查（柠版 GetAtlas() 对
    mod 物品回落 inventoryimages4 → 面板图标空白）。每次运行重生成，幂等。返回条数。"""
    pre = os.path.join(target, 'preload_assets_auto.lua')
    if not os.path.isfile(pre):
        return 0
    txt = open(pre, encoding='utf-8-sig', errors='replace').read()
    paths = re.findall(r'"([^"]+)"', txt)
    if not paths:
        return 0
    inv = [p for p in paths if '/images/inventoryimages/' in p]
    rest = [p for p in paths if '/images/inventoryimages/' not in p]
    ordered = list(dict.fromkeys(inv + rest))
    lines = [
        '\ufeff-- Generated automatically. Do not edit.',
        '-- 本 mod 全部 ATLAS 资源（来源 preload_assets_auto.lua，路径为柠版实际文件路径）。',
        '-- 用途：__TR_FIND_ATLAS 反查——柠版 inventoryitem:GetAtlas() 解析不出 mod 图集时会回落',
        '-- images/inventoryimages4.xml，面板 SetTexture 就找不到 region。',
        '-- 柠版 AtlasContains 认的是 scripts/mods/<mod>/... 实际路径（依据 APK 内置 mod 的 test.lua）。',
        '-- 排序：images/inventoryimages/ 优先，命中更快。',
        'return {',
    ]
    for p in ordered:
        lines.append('    "%s",' % p)
    lines.append('}')
    out = os.path.join(target, 'scripts', 'tr_atlas_index_auto.lua')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    return len(ordered)


def inject_prefab_global_shim(target, modname):
    """★ 预制物全局垫片 + 图标图集反查（v1.6.1，实机日志实施）：
    框架在 idle 阶段批量 restore mod 预制物，早于原版 prefablist → 由原版预制物文件
    「顺带定义」的 GetAllWinterOrnamentPrefabs / ASSETS 还不存在，mod 文件首行即报错，
    整文件作废（虚空异界实测丢 8 个预制物）。这里预置语义等价兜底，原版稍后加载会覆盖回来。
    同时注入 __TR_FIND_ATLAS：柠版 GetAtlas() 对 mod 物品回落 inventoryimages4，
    面板用 AtlasContains 在 scripts/tr_atlas_index_auto.lua 的清单里反查真实图集。
    幂等 __FW_PREFAB_GLOBAL_SHIM。返回 1 注入 / 0 跳过。"""
    modmain_p = os.path.join(target, 'modmain.lua')
    if not os.path.isfile(modmain_p):
        return 0
    raw = open(modmain_p, 'rb').read()
    mm = raw.decode('utf-8-sig', errors='replace')
    if '__FW_PREFAB_GLOBAL_SHIM' in mm:
        return 0  # 幂等
    block = (PREFAB_GLOBAL_SHIM_BLOCK.replace('@@MOD@@', modname))
    mm = mm.rstrip() + '\n\n' + block
    out = mm.encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        out = b'\xef\xbb\xbf' + out
    open(modmain_p, 'wb').write(out)
    return 1


PREFAB_GLOBAL_SHIM_BLOCK = r'''
-- 柠版预制物全局垫片（GetAllWinterOrnamentPrefabs / ASSETS，v1.6.1 工具注入）
-- 现象：client_log 里 sim prefab restore failed file=fh_baozangdai
--       err=attempt to call global 'GetAllWinterOrnamentPrefabs' (a nil value)；
--       file=tr_waxed_plants err=variable 'ASSETS' is not declared → 8 个预制物整文件作废。
-- 根因：框架在 idle 阶段批量 restore mod 预制物，早于原版 prefablist 跑完。这两个全局由原版
--       prefabs/winter_ornaments.lua（prefablist 第 1343/1443 条，几乎排最后）与
--       prefabs/waxed_plants.lua「顺带定义」，此刻都还不存在。
-- 处置：预置语义等价的兜底。原版稍后加载时会用自己的赋值覆盖回来，PC 端行为不变。
if GLOBAL.rawget(GLOBAL, "__FW_PREFAB_GLOBAL_SHIM") == nil then
    GLOBAL.rawset(GLOBAL, "__FW_PREFAB_GLOBAL_SHIM", true)

    -- ① GetAllWinterOrnamentPrefabs()：原版由 MakeOrnament 逐个 push "winter_ornament_"..id，
    --    共 70 项（显式 42 + plain1-12 + fancy1-8 + light1-8），此处等价重建。
    if GLOBAL.rawget(GLOBAL, "GetAllWinterOrnamentPrefabs") == nil then
        local ORNAMENT_LIST = {
        "winter_ornament_festivalevents1","winter_ornament_festivalevents2",
        "winter_ornament_festivalevents3","winter_ornament_festivalevents4",
        "winter_ornament_festivalevents5","winter_ornament_boss_antlion",
        "winter_ornament_boss_bearger","winter_ornament_boss_beequeen",
        "winter_ornament_boss_deerclops","winter_ornament_boss_dragonfly",
        "winter_ornament_boss_fuelweaver","winter_ornament_boss_klaus",
        "winter_ornament_boss_krampus","winter_ornament_boss_moose",
        "winter_ornament_boss_noeyeblue","winter_ornament_boss_noeyered",
        "winter_ornament_boss_toadstool","winter_ornament_boss_malbatross",
        "winter_ornament_boss_crabking","winter_ornament_boss_crabkingpearl",
        "winter_ornament_boss_minotaur","winter_ornament_boss_toadstool_misery",
        "winter_ornament_boss_hermithouse","winter_ornament_boss_pearl",
        "winter_ornament_boss_celestialchampion1","winter_ornament_boss_celestialchampion2",
        "winter_ornament_boss_celestialchampion3","winter_ornament_boss_celestialchampion4",
        "winter_ornament_boss_eyeofterror1","winter_ornament_boss_eyeofterror2",
        "winter_ornament_boss_wagstaff","winter_ornament_boss_daywalker",
        "winter_ornament_shadowthralls","winter_ornament_boss_mutateddeerclops",
        "winter_ornament_boss_mutatedbearger","winter_ornament_boss_mutatedwarg",
        "winter_ornament_boss_daywalker2","winter_ornament_boss_sharkboi",
        "winter_ornament_boss_wormboss","winter_ornament_boss_celestialrevenant",
        "winter_ornament_boss_warbot","winter_ornament_boss_celestialscion",
        "winter_ornament_plain1","winter_ornament_plain2","winter_ornament_plain3",
        "winter_ornament_plain4","winter_ornament_plain5","winter_ornament_plain6",
        "winter_ornament_plain7","winter_ornament_plain8","winter_ornament_plain9",
        "winter_ornament_plain10","winter_ornament_plain11","winter_ornament_plain12",
        "winter_ornament_fancy1","winter_ornament_fancy2","winter_ornament_fancy3",
        "winter_ornament_fancy4","winter_ornament_fancy5","winter_ornament_fancy6",
        "winter_ornament_fancy7","winter_ornament_fancy8","winter_ornament_light1",
        "winter_ornament_light2","winter_ornament_light3","winter_ornament_light4",
        "winter_ornament_light5","winter_ornament_light6","winter_ornament_light7",
        "winter_ornament_light8",
        }
        GLOBAL.rawset(GLOBAL, "GetAllWinterOrnamentPrefabs", function()
            local copy = {}
            for i = 1, #ORNAMENT_LIST do copy[i] = ORNAMENT_LIST[i] end
            return copy
        end)
    end

    -- ② ASSETS：原版 waxed_plants.lua 顶层就是一条 SCRIPT 资源，等价重建。
    if GLOBAL.rawget(GLOBAL, "ASSETS") == nil then
        GLOBAL.rawset(GLOBAL, "ASSETS", { GLOBAL.Asset("SCRIPT", "scripts/prefabs/waxed_plant_common.lua") })
    end
end

-- 柠版 mod 物品图标图集反查（v1.6.1 工具注入）
-- 现象：长按 mod 物品，面板图标空白，日志 Could not find region 'konghuangxianglian.tex'
--       from atlas 'images/inventoryimages4.xml'（原版物品一次都不刷）。
-- 根因：柠版客户端 inventoryitem:GetAtlas() 解析不出 mod 图集时回落 inventoryimages4（原版合并
--       图集），而 region 实际在 mod 自己的图集里（images/inventoryimages/konghuangxianglian.xml、
--       images/inventoryimages/xygj.xml）。
-- 处置：用 TheSim:AtlasContains 在本 mod 的图集清单里反查真实图集，按 tex 缓存（含负缓存）。
--       ★ 柠版 AtlasContains 认的是 scripts/mods/<mod>/... 实际路径，不是 Asset() 声明名
--         （依据 APK 内置 mod 的 test.lua：储藏室/几何布局/神奇西瓜刀）。
if GLOBAL.rawget(GLOBAL, "__TR_FIND_ATLAS") == nil then
    local ATLAS_LIST = nil
    local ATLAS_SET = nil
    local ATLAS_CACHE = {}
    local ATLAS_ROOTS = {
        "scripts/mods/@@MOD@@/images/inventoryimages/",
        "images/inventoryimages/",
    }

    local function LoadAtlasList()
        if ATLAS_LIST ~= nil then return ATLAS_LIST end
        local loaders = {
            function() return GLOBAL.require("tr_atlas_index_auto") end,
            function() return GLOBAL.require("scripts/tr_atlas_index_auto") end,
            function()
                local kll = GLOBAL.rawget(GLOBAL, "kleiloadlua")
                if type(kll) ~= "function" then return nil end
                local chunk = kll("scripts/mods/@@MOD@@/scripts/tr_atlas_index_auto.lua")
                if type(chunk) ~= "function" then return nil end
                return chunk()
            end,
        }
        for i = 1, #loaders do
            local ok, list = GLOBAL.pcall(loaders[i])
            if ok and type(list) == "table" and #list > 0 then
                ATLAS_LIST = list
                return ATLAS_LIST
            end
        end
        ATLAS_LIST = false
        return ATLAS_LIST
    end

    local function LoadAtlasSet()
        if ATLAS_SET ~= nil then return ATLAS_SET end
        LoadAtlasList()
        if ATLAS_LIST then
            local set = {}
            for i = 1, #ATLAS_LIST do set[ATLAS_LIST[i]] = true end
            ATLAS_SET = set
        else
            ATLAS_SET = false
        end
        return ATLAS_SET
    end

    function GLOBAL.__TR_FIND_ATLAS(tex, prefab)
        if type(tex) ~= "string" or tex == "" then return nil end
        local cached = ATLAS_CACHE[tex]
        if cached ~= nil then return cached or nil end

        local sim = GLOBAL.TheSim
        if sim == nil or sim.AtlasContains == nil then return nil end
        local found = nil

        -- 快路径：物品图集通常就叫 <prefab>.xml。只试清单里真实存在的路径，
        -- 避免对不存在的 atlas 调 AtlasContains（会刷 AtlasContains 失败日志）。
        local set = LoadAtlasSet()
        if set and type(prefab) == "string" and prefab ~= "" then
            for i = 1, #ATLAS_ROOTS do
                local guess = ATLAS_ROOTS[i] .. prefab .. ".xml"
                if set[guess] then
                    local ok, has = GLOBAL.pcall(sim.AtlasContains, sim, guess, tex)
                    if ok and has then found = guess; break end
                end
            end
        end

        -- 慢路径：线性扫本 mod 图集清单（konghuangxianglian 走快路径，xygj 这类走慢路径）
        if found == nil and ATLAS_LIST then
            for i = 1, #ATLAS_LIST do
                local ok, has = GLOBAL.pcall(sim.AtlasContains, sim, ATLAS_LIST[i], tex)
                if ok and has then found = ATLAS_LIST[i]; break end
            end
        end

        ATLAS_CACHE[tex] = found or false
        return found
    end
end
'''


def inject_register_character(target, modname):
    """★ 角色 mod 自动生成 FW_RegisterCharacter 调用（v1.5.0，§22.6-6 实施）：
    检测 modmain 用 AddModCharacter 注册新角色但未用 FW_RegisterCharacter → 从
    TUNING.<PREFAB>_HEALTH/HUNGER/SANITY 读 stats（读不到用 150）自动生成注入。
    mod 已用 FW_RegisterCharacter（新版框架）→ 跳过。幂等 __fw_registerchar。返回 1/0。"""
    modmain_p = os.path.join(target, 'modmain.lua')
    if not os.path.isfile(modmain_p):
        return 0
    raw = open(modmain_p, 'rb').read()
    mm = raw.decode('utf-8-sig', errors='replace')
    if '__fw_registerchar' in mm or 'FW_RegisterCharacter(' in mm:
        return 0  # 幂等 / mod 已用新版框架调用（注释提及不算）
    m = re.search(r'AddModCharacter\s*\(\s*["\x27]([A-Za-z_]\w*)["\x27]', mm)
    if not m:
        return 0
    prefab = m.group(1)
    stats = {'health': 150, 'hunger': 150, 'sanity': 150}
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            try:
                t = open(os.path.join(r, f), 'rb').read().decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            for k, field in (('_HEALTH', 'health'), ('_HUNGER', 'hunger'), ('_SANITY', 'sanity')):
                sm = re.search(r'TUNING\s*\.\s*%s%s\s*=\s*(\d+)' % (re.escape(prefab.upper()), k), t, re.I)
                if sm:
                    stats[field] = int(sm.group(1))
    # title：STRINGS.CHARACTERS.<PREFAB>.NAME（拿不到用 prefab）
    title = prefab
    tsm = re.search(r'STRINGS\s*\.\s*CHARACTERS\s*\.\s*%s\s*\.\s*NAME\s*=\s*["\x27]([^"\x27]+)["\x27]' % re.escape(prefab.upper()), mm)
    if tsm:
        title = tsm.group(1)
    block = (
        '\n\n-- 柠版角色框架：FW_RegisterCharacter 自动生成（__fw_registerchar 幂等，v1.5.0 工具注入）\n'
        '-- 角色入列三件套之一（FW_LoadPrefabs + FW_PreloadAssets + FW_RegisterCharacter），\n'
        '-- 自动写 TUNING.<PREFAB>_HEALTH/HUNGER/SANITY 并加入 MODCHARACTERLIST。\n'
        'if type(GLOBAL.FW_RegisterCharacter) == "function" then\n'
        '    GLOBAL.FW_RegisterCharacter(%s, {\n'
        '        prefab = "%s", register = AddModCharacter,\n'
        '        gender = "UNKNOWN", name = "%s", title = "%s",\n'
        '        description = "", quote = "", survivability = "未知",\n'
        '        health = %d, hunger = %d, sanity = %d,\n'
        '        skins = {"%s_none"},\n'
        '    })\n'
        'end' % (repr(modname), prefab, prefab, title, stats['health'], stats['hunger'], stats['sanity'], prefab))
    mm = mm.rstrip() + block + '\n'
    out = mm.encode('utf-8')
    if raw.startswith(b'\\xef\\xbb\\xbf'):
        out = b'\\xef\\xbb\\xbf' + out
    open(modmain_p, 'wb').write(out)
    return 1


def inject_key_buttons(target, modname, use_simulate=False, character=''):
    """★ 角色按键技能 → 柠版按钮（v1.4.23，千年狐/晓美焰按键技能实证通用化）：
    手机端无键盘，PC 角色 Mod 的按键技能（keyhandler 控制键转发 / TheInput 键盘钩子）
    在柠版无法触发。扫描全部 lua 提取 (RPC表达式, 按键) → modmain 尾部注入
    FW_RegisterModButton，onpress 复用原始 SendModRPCToServer 调用（同参数同 RPC）。
    两类实证模式：
    a) 控制键转发（千年狐）：OnControlDown 内 SendModRPCToServer(MOD_RPC[keyhandler], KEY_R, true, nil)
    b) 键盘钩子（晓美焰）：old_key(self, key, down) 内 key == SKILLKEY and down → SendModRPCToServer(MOD_RPC.timepause)
    v1.4.24 补全扫描通道（借鉴《柠版模组一键适配器》MT v1.6.1 KeyScanner）：
    c) OnRawKey 反序比较 KEY_X == key（原只匹配 key == X）
    d) AddKeyDownHandler/AddKeyUpHandler 直连注册回调（取回调体内首个 SendModRPCToServer）
    e) 别名回填：local X = "KEY_Y" / X = "KEY_Y" → key == X 换算为 KEY_Y
    f) 鼠标键：MOUSEBUTTON_(LEFT|RIGHT|MIDDLE) 与 SendModRPCToServer 同块 → 按钮模拟左/右/中键
    g) 配置键：key == cfgvar 且 cfgvar 来自 GetModConfigData("name") → 用 modinfo 默认值
       （解析不到默认值则跳过并提示，不注入动态键）
    use_simulate=True（--simulate-key）时：onpress 优先 FW_SimulateKey(keycode, phase)
    模拟按键（判空 + pcall，不可用回退 RPC）——借鉴不灵小姐防御式写法，默认关闭。
    去重（图标按钮可能也有对应键盘按键常量，不重复注册）：
    ①同一 RPC 表达式只注册一次；②Mod 已存在 FW_RegisterModButton 且注册块内含
    相同 RPC → 视为已有图标按钮，跳过；③注入幂等标记 __fw_keybutton。
    返回注册数。"""
    modmain_p = os.path.join(target, 'modmain.lua')
    if not os.path.isfile(modmain_p):
        return 0
    try:
        raw = open(modmain_p, 'rb').read()
        mm = raw.decode('utf-8-sig', errors='replace')
    except Exception:
        return 0
    if '__fw_keyaction' in mm:
        return 0  # 幂等：已注入过

    # 预收集 Mod 已存在的 FW_RegisterModButton 注册块（去重基准：图标按钮已注册 → 按键不重复）
    existing_blocks = []
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p2 = os.path.join(r, f)
            try:
                t2 = open(p2, 'rb').read().decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            if 'FW_RegisterModButton' in t2:
                # 只收集 FW_RegisterModButton 注册块内部文本（括号深度找闭合 `})`），
                # 防止文件其它位置（如按键技能自身 SendModRPCToServer 调用）的同 RPC
                # 字符串被误判为"已有图标按钮已注册"而跳过注入（v1.5.0 冒烟实证修复）
                for bm in re.finditer(r'FW_RegisterModButton\s*\(', t2):
                    depth = 0
                    j = bm.start()
                    while j < len(t2):
                        ch = t2[j]
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth <= 0:
                                break
                        j += 1
                    existing_blocks.append(t2[bm.start():j + 1])

    def norm_rpc(s):
        s = re.sub(r'\[["\'](\w+)["\']\]', r'.\1', s)
        return re.sub(r'\s+', '', s).replace('GLOBAL.', '')

    def already_registered(rpc):
        nr = norm_rpc(rpc)
        for t2 in existing_blocks:
            if nr in t2:
                return True
        return False

    ctrl_ctx = re.compile(
        r'OnControlDown|OnControlUp|ControlDown|ControlUp|keyhandler|KeyDown|KeyUp|'
        r'TheInput|InputHandler|IsControlPressed|OnKeyDown|OnKeyUp|AddKeyDownHandler|AddKeyUpHandler|OnMouseButton')

    # modinfo 配置默认值（模式 g 配置键通道：key == cfgvar 且 cfgvar 来自
    # GetModConfigData("name") → 用 modinfo 里该配置的 default 作为注入键）
    cfg_defaults = {}
    minfo_p = os.path.join(target, 'modinfo.lua')
    if os.path.isfile(minfo_p):
        try:
            mtxt = open(minfo_p, encoding='utf-8', errors='replace').read()
            for cm in re.finditer(
                    r'name\s*=\s*["\'](\w+)["\']\s*,[^{}]{0,400}?default\s*=\s*["\']?([A-Za-z0-9_]+)["\']?',
                    mtxt, re.S):
                cfg_defaults[cm.group(1)] = cm.group(2)
        except Exception:
            pass

    found = []          # (rpc, keyexpr, label, phase)
    seen_rpc = set()
    skip_note = []

    def add_found(rpc, keyexpr, label, src, phase=None):
        """统一去重 + 安全注入：同 RPC 只注册一次；已存在图标按钮同 RPC 跳过；局部变量 RPC 跳过。"""
        rpc = rpc.strip()
        if rpc in seen_rpc or already_registered(rpc):
            skip_note.append('%s: 同 RPC(%s) 已注册/已存在图标按钮，跳过去重' % (src, rpc))
            return
        if re.fullmatch(r'[A-Za-z_]\w*', rpc):
            skip_note.append('%s: rpc=%s 为局部变量，无法安全注入' % (src, rpc))
            return
        seen_rpc.add(rpc)
        found.append((rpc, keyexpr, label, phase))

    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p2 = os.path.join(r, f)
            try:
                text = open(p2, 'rb').read().decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            src = os.path.relpath(p2, target)

            # 模式 e：文件级别名表 local X = "KEY_Y" / X = "KEY_Y"（行尾赋值，防误匹配函数体）
            alias_map = {}
            for am in re.finditer(
                    r'(?m)^\s*(?:local\s+)?([A-Za-z_]\w*)\s*=\s*["\']?(?:GLOBAL\.)?(KEY_[A-Za-z0-9_]+)["\']?\s*$',
                    text):
                alias_map[am.group(1)] = am.group(2)

            # 模式 g：配置变量名 → 配置名（local cfgkey = GetModConfigData("skillkey")）
            cfgvar_map = {}
            for am in re.finditer(r'local\s+([A-Za-z_]\w*)\s*=\s*GetModConfigData\s*\(\s*["\x27](\w+)["\x27]\s*\)', text):
                cfgvar_map[am.group(1)] = am.group(2)

            def resolve_key(tok):
                """KEY_X / GLOBAL.KEY_X 直用；别名→KEY_Y；配置名→modinfo 默认键（仅 KEY_ 形式）。"""
                tok = tok.strip()
                if re.fullmatch(r'(?:GLOBAL\.)?KEY_[A-Za-z0-9_]+', tok):
                    return tok
                if tok in alias_map:
                    return alias_map[tok]
                cfgname = cfgvar_map.get(tok)
                if cfgname and cfgname in cfg_defaults and re.fullmatch(r'(?:GLOBAL\.)?KEY_[A-Za-z0-9_]+', cfg_defaults[cfgname]):
                    return cfg_defaults[cfgname]
                return None

            # 模式 a：控制键转发 SendModRPCToServer(rpc, KEY_X, true/false)
            for m in re.finditer(
                    r"SendModRPCToServer\s*\(\s*([^,)]+?)\s*,\s*((?:GLOBAL\.)?KEY_[A-Z_0-9]+)\s*,\s*(?:true|false)",
                    text):
                rpc = m.group(1).strip()
                key = m.group(2).strip()
                ctx = text[max(0, m.start() - 300):m.end() + 300]
                if not ctrl_ctx.search(ctx):
                    continue
                phase = 'up' if re.search(r'OnControlUp|ControlUp', ctx) else 'down'
                add_found(rpc, key, key_btn_label(key), src, phase)

            # 模式 b+c：键盘钩子 key==X and down（正序 + OnRawKey 反序 KEY_X==key，
            # 兼容别名/配置键换算；回调签名须含 key/down 参数）
            for m in re.finditer(
                    r"\b(?:key\s*==\s*([\w.]+)|((?:GLOBAL\.)?KEY_[A-Za-z0-9_]+|[\w.]+)\s*==\s*key)\s+and\s+down\b",
                    text):
                tok = (m.group(1) or m.group(2)).strip()
                pre = text[max(0, m.start() - 400):m.start()]
                fns = list(re.finditer(r'function\s*[\w.:]*\s*\(([^)\n]*)\)', pre))
                fnm = fns[-1] if fns else None
                sig = fnm.group(1) if fnm else ''
                if 'key' not in sig or 'down' not in sig:
                    continue  # 非键盘回调签名（支持 function self:OnRawKey(key, down, ...) 冒号定义）
                win = text[m.end():m.end() + 600]
                ep = win.find('\nend')
                if ep >= 0:
                    win = win[:ep]
                sm = re.search(r"SendModRPCToServer\s*\(\s*([^,)]+)", win)
                if not sm:
                    continue
                rpc = sm.group(1).strip()
                keyexpr = resolve_key(tok)
                if keyexpr is None and not re.fullmatch(r'(?:GLOBAL\.)?KEY_[A-Za-z0-9_]+', tok):
                    keyexpr = None  # 动态/局部值：不携带按键（仍注册 RPC 按钮）
                add_found(rpc, keyexpr, key_btn_label(tok), src, 'down')

            # 模式 d：AddKeyDownHandler/AddKeyUpHandler 直连注册（取回调体内首个 RPC）
            for m in re.finditer(
                    r"Add(?:KeyDown|KeyUp)Handler\s*\(\s*((?:GLOBAL\.)?KEY_[A-Za-z0-9_]+|[\w.]+)\s*,",
                    text):
                tok = m.group(1).strip()
                keyexpr = resolve_key(tok)
                if keyexpr is None:
                    continue
                win = text[m.end():m.end() + 800]
                ep = win.find('\nend')
                if ep >= 0:
                    win = win[:ep]
                sm = re.search(r"SendModRPCToServer\s*\(\s*([^,)]+)", win)
                if not sm:
                    continue
                phase = 'up' if 'KeyUpHandler' in m.group(0) else 'down'
                add_found(sm.group(1).strip(), keyexpr, key_btn_label(tok), src, phase)

            # 模式 f：鼠标键（MOUSEBUTTON_* 与 SendModRPCToServer 同块 → 按钮模拟左/右/中键）
            # 窗口只向后 400 字符（往前会撞到上一函数的 RPC，LOL 图鉴鼠标键实证）
            for m in re.finditer(r"MOUSEBUTTON_(LEFT|RIGHT|MIDDLE)", text):
                ctx = text[m.start():m.start() + 400]
                sm = re.search(r"SendModRPCToServer\s*\(\s*([^,)]+)", ctx)
                if not sm:
                    continue
                btn = {'LEFT': 'MOUSEBUTTON_LEFT', 'RIGHT': 'MOUSEBUTTON_RIGHT', 'MIDDLE': 'MOUSEBUTTON_MIDDLE'}[m.group(1)]
                lbl = {'LEFT': '左键', 'RIGHT': '右键', 'MIDDLE': '中键'}[m.group(1)]
                add_found(sm.group(1).strip(), btn, lbl, src, None)  # 鼠标键无 keycode，仅按钮

    if not found:
        for s in skip_note:
            print('     [跳过]', s)
        return 0
    blocks = []
    for i, (rpc, keyexpr, label, phase) in enumerate(found):
        if keyexpr and use_simulate and re.search(r'KEY_', keyexpr):
            # --simulate-key：onpress 优先 FW_SimulateKey(keycode, phase) 模拟按键
            # （判空 + pcall；不可用回退 RPC）——借鉴不灵小姐防御式写法
            press = (
                "local _sim = GLOBAL.rawget(GLOBAL, \"FW_SimulateKey\")\n"
                "            if type(_sim) == \"function\" then\n"
                "                local _ok = GLOBAL.pcall(_sim, %s, true)\n"
                "                if _ok then GLOBAL.pcall(_sim, %s, false) end\n"
                "            else\n"
                "                SendModRPCToServer(%s, %s, true, nil)\n"
                "            end" % (keyexpr, keyexpr, rpc, keyexpr))
        elif keyexpr:
            press = 'SendModRPCToServer(%s, %s, true, nil)' % (rpc, keyexpr)
        else:
            press = 'SendModRPCToServer(%s)' % rpc
        is_key = bool(keyexpr) and bool(re.search(r'KEY_', keyexpr))
        char_field_a = ('                character = %s,\n' % repr(character)) if character else ''
        char_field_b = ('            character = %s,\n' % repr(character)) if character else ''
        act_block = ''
        if is_key:
            # v1.5.0: 新版框架 FW_RegisterAction 成对注册（按键动作 + 触屏 source 区分），
            # reuse_action=true 按钮复用动作；keyboard_phase 按扫描通道（down/up）传递。
            act_block = (
                "        if _has_action then\n"
                "            GLOBAL.FW_RegisterAction(%s, \"KEYBTN_%d\", {\n"
                "                keycode = %s,\n"
                "                keyboard_phase = \"%s\",\n"
                "%s"
                "                onpress = function(player, source)\n"
                "                    %s\n"
                "                end,\n"
                "            })\n"
                "        end\n" % (repr(modname), i + 1, keyexpr, phase or 'down', char_field_a, press))
        blocks.append(
            "do\n"
            "    local _has_action = type(GLOBAL.FW_RegisterAction) == \"function\"\n"
            + act_block +
            "    if type(GLOBAL.FW_RegisterModButton) == \"function\" then\n"
            "        GLOBAL.FW_RegisterModButton(%s, {\n"
            "            key = \"KEYBTN_%d\",\n"
            "            label = \"%s\",\n"
            "%s"
            "            reuse_action = _has_action,\n"
            "            onpress = _has_action and nil or function()\n"
            "                %s\n"
            "            end,\n"
            "        })\n"
            "    end\n"
            "end" % (repr(modname), i + 1, label, char_field_b, press))
    inject = ('\n\n-- 柠版适配: 角色按键技能 → FW_RegisterAction + 柠版按钮（__fw_keyaction 幂等，去重: 同 RPC 只注册一次）\n'
              '-- (PC 键盘触发在手机端不可用, 转框架动作+按钮栏按钮; 新版框架 FW_RegisterAction(reuse_action)\n'
              '--  成对注册, 旧框架回退纯按钮 onpress RPC; 已有图标按钮的同功能不重复注册)\n'
              + '\n'.join(blocks))
    mm = mm.rstrip() + '\n' + inject + '\n'
    out = mm.encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        out = b'\xef\xbb\xbf' + out
    open(modmain_p, 'wb').write(out)
    print('   - [按键按钮] %s: 按键技能 → FW_RegisterAction+柠版按钮 %d 个%s' %
          (os.path.relpath(modmain_p, target), len(found), '（带 character=' + character + '）' if character else ''))
    for s in skip_note:
        print('     [跳过]', s)
    return len(found)


def convert_registerprefabs_hook(target):
    """★ 通用 ModManager.RegisterPrefabs hook 转换（英雄联盟武器金锅配方的通用化）：
    PC 老 Mod 把初始化逻辑挂在 `ModManager.RegisterPrefabs = function(self, ...) ... end`
    （在 PrefabFiles 加载前执行）——柠版用 FW_LoadPrefabs 加载，该 hook 不触发 → 逻辑丢失。
    自动改为 `AddSimPostInit` + `TheWorld:DoTaskInTime(0, ...)` 延迟执行（时机晚于所有
    模组注册，逻辑等价）。hook 体引用 self/...（依赖原调用参数）时跳过并报告。
    返回转换数。"""
    n = 0
    kw_re = re.compile(r'GLOBAL\.ModManager\.RegisterPrefabs\s*=\s*function\(([^)]*)\)')
    for r, dirs, files in os.walk(target):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
                text = raw.decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            if 'RegisterPrefabs' not in text or '__fw_hook_conv' in text:
                continue
            m = kw_re.search(text)
            if not m:
                continue
            params = m.group(1)
            # 提取 function 体：Lua 关键字平衡（if/for/while/function → end）。
            # depth 从 1 起（m.end() 后的首行已进入 function 体内），减到 0 = 闭合 end。
            start = m.end()
            depth = 1
            lines = text[start:].split('\n')
            body_lines = []
            end_line = None
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if '--' in stripped:
                    stripped = re.sub(r'--.*', '', stripped)
                depth += len(re.findall(r'\b(?:if|for|while|function)\b', stripped))
                depth -= len(re.findall(r'\bend\b', stripped))
                body_lines.append(line)
                if depth <= 0:
                    end_line = idx
                    break
            if end_line is None:
                continue
            body = '\n'.join(body_lines[:-1])  # 去掉 end
            body = re.sub(r'^\s*oldRegisterPrefabs\s*\([^)]*\)\s*$', '', body, flags=re.M)
            if re.search(r'\bself\b|\b\.\.\.\b', body):
                print('   - [跳过] %s: hook 体引用 self/...（无法安全延迟执行）' % os.path.relpath(p, target))
                continue
            inject = (
                '\n-- 柠版适配: PC 版挂在 ModManager.RegisterPrefabs hook 的逻辑在柠版不触发\n'
                '-- (柠版用 FW_LoadPrefabs 加载预制物), 改为 AddSimPostInit + 延迟1帧直接执行\n'
                '-- __fw_hook_conv: 已由适配工具转换\n'
                'AddSimPostInit(function()\n'
                '    if TheWorld then\n'
                '        TheWorld:DoTaskInTime(0, function()\n'
                + body +
                '\n        end)\n'
                '    end\n'
                'end)\n'
            )
            text = text[:m.start()] + inject + text[start + len('\n'.join(body_lines)) + 1:]
            out = text.encode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf'):
                out = b'\xef\xbb\xbf' + out
            open(p, 'wb').write(out)
            n += 1
    return n


def inject_scrollablelist_drag(target):
    """★ ScrollableList 系拖动重写（v1.4.5，LOL 图鉴左侧拖动无效实证）：
    标准 ScrollableList（position_marker + DoDragScroll + Scroll(步数)）在柠版触摸下，
    原版 DoDragScroll 用 TheFrontEnd.lasty 直接 SetPosition + GetWorldPosition/
    GetHierarchicalScale 坐标换算——嵌套层级深（图鉴左侧列表在 content_wrap 内）时
    换算错乱 → 拖动滑块无效（上下按钮正常，LOL 手工版实证）。
    手工版重写 = 手指屏幕 y 映射滑轨比例 → ScrollToRatio(_target_offset) →
    OnUpdate 每帧单调逼近（TrueScrollArea target 机制）。对全部 ScrollableList 系
    自动注入同构方案：
    a) SetOnDown 立即 TheFrontEnd:LockFocus(true) + self.dragging=true（拖动通道接通前提）
    b) Scroll 开头 self._target_offset=nil（手动滚动打断残留插值，防反向叠加振荡）
    c) DoDragScroll 重写（手指 y→滑轨比例→ScrollToRatio，不临时移动手柄）
    d) ScrollToRatio 方法（设目标步数；缺失才注入）
    e) OnUpdate 方法（每帧 ±1 步逼近，到目标清空；基类每帧调用，缺失才注入）
    与 --touch-scroll 跳过条件一致（DoDragScroll + position_marker），两者互斥不重复。
    返回注入文件数。"""
    base = os.path.join(target, 'scripts')
    if not os.path.isdir(base):
        return 0
    n = 0
    for r, dirs, files in os.walk(base):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
                text = raw.decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            if '__fw_drag_rewrite' in text:
                continue  # 已注入（幂等）
            if 'DoDragScroll' not in text or 'position_marker' not in text:
                continue
            m = re.search(r'local\s+(\w+)\s*=\s*Class\(', text)
            if not m:
                continue
            cls = m.group(1)
            if 'arrow_button_size' not in text or 'self.height' not in text:
                continue  # 缺标准字段（非标准 ScrollableList），跳过防破坏
            changed = False
            lines = text.split('\n')

            # a) SetOnDown 注入：LockFocus(true) + dragging + 按下坐标兜底 + StartUpdating
            #    （手工版 pedia 同构：按下立即锁焦点并进入拖动；触屏 lastx/lasty 可能 nil 先记录；
            #     StartUpdating 启用每帧 OnUpdate——★ 手工版在 ctor 调用，无 ctor 锚点时这里兜底，
            #     保证 _target_offset 有人消费，否则拖动设了目标但 OnUpdate 不跑=划不动，v1.4.6 实证）
            for i, l in enumerate(lines):
                if 'self.position_marker:SetOnDown(' in l and 'function' in l:
                    lines.insert(i + 1, '        TheFrontEnd:LockFocus(true)')
                    lines.insert(i + 2, '        self.dragging = true')
                    lines.insert(i + 3, '        self._drag_lastx = TheFrontEnd.lastx')
                    lines.insert(i + 4, '        self._drag_lasty = TheFrontEnd.lasty')
                    lines.insert(i + 5, '        -- v1.4.16: 记录按下时 marker 屏幕/局部 y 作 DoDragScroll 固定基准')
                    lines.insert(i + 6, '        --   (拖动中不更新 → 消除 OnUpdate 移动 marker 造成的反馈振荡)')
                    lines.insert(i + 7, '        local _mkp = self.position_marker')
                    lines.insert(i + 8, '        self._drag_marker_wy = _mkp and _mkp:GetWorldPosition().y or 0')
                    lines.insert(i + 9, '        self._drag_marker_ly = _mkp and _mkp:GetPosition().y or 0')
                    lines.insert(i + 10, '        self:StartUpdating()')
                    changed = True
                    break

            # a2) SetWhileDown 重写（手工版 pedia 同构）：无 do_dragging 守卫（触摸拖动可能
            #     不触发 OnDown 设 do_dragging），GetStaticTime 0.05s 节流直调 DoDragScroll
            text1 = '\n'.join(lines)
            mwd = re.search(
                r'self\.position_marker:SetWhileDown\(\s*function\(\)\s*\n', text1)
            if mwd:
                lines2 = text1.split('\n')
                start_line = text1[:mwd.start()].count('\n')
                depth = 0
                end_line = None
                for j in range(start_line, len(lines2)):
                    l = lines2[j]
                    depth += l.count('function') + (l.count('if ') - l.count('elseif ')) + l.count('for ') + l.count('while ')
                    depth -= l.count('end')
                    if depth <= 0 and 'end' in l and j > start_line:
                        end_line = j
                        break
                if end_line is not None:
                    wd_new = (
                        '    self.position_marker:SetWhileDown( function()\n'
                        '        -- 柠版适配: 无守卫节流直调(手工版同构): 触摸拖动不依赖 do_dragging 标志\n'
                        '        -- v1.4.15: marker 自身 OnTouch 拖动激活时跳过(双通道竞争: OnTouchMove\n'
                        '        --   与 DoDragScroll 同时写 _target_offset → 目标来回跳 = 闪烁)\n'
                        '        if self.position_marker and self.position_marker._mk_active then return end\n'
                        '        if not self.last_drag_time or GetStaticTime() - self.last_drag_time > 0.05 then\n'
                        '            self.last_drag_time = GetStaticTime()\n'
                        '            self:DoDragScroll()\n'
                        '        end\n'
                        '    end)\n')
                    line_starts = []
                    acc = 0
                    for l in lines2:
                        line_starts.append(acc)
                        acc += len(l) + 1
                    end_start = line_starts[end_line]
                    end_len = len(lines2[end_line])
                    text1 = text1[:mwd.start()] + wd_new + text1[end_start + end_len:]
                    changed = True

            # a3) ctor 注入 StartUpdating（手工版 ctor 尾部同构：DoFocusHookups 后启用每帧
            #     OnUpdate + 初始化 _target_offset）。只在 ctor 未注入时补（a 段 SetOnDown 已兜底；
            #     DST EnableUpdate 重复调用幂等无害）
            if not re.search(r'self:DoFocusHookups\(\)\s*\n\s*self\._target_offset\s*=\s*nil\s*\n\s*self:StartUpdating\(\)', text1):
                pat_ctor = re.compile(r'(self:DoFocusHookups\(\)\s*\n)')
                m4 = pat_ctor.search(text1)
                if m4:
                    text1 = (text1[:m4.end()] +
                             '    self._target_offset = nil\n'
                             '    self:StartUpdating()\n' +
                             text1[m4.end():])
                    changed = True

            # a5) 列表本体触摸拖动（v1.4.14，LOL"左侧列表拖不动"实证）：
            #     手工版 ScrollingGrid 列表区域原生触摸滑动；ScrollableList 子类无触摸
            #     处理 → 划列表内容无响应。v1.4.13 用 FW_BindWidgetTouch 无效（其拖动
            #     语义是移动 widget 位置，onmove 不回调坐标）。改用 DST 移动版原生
            #     widget 触摸分发 OnTouchStart(id,x,y)/OnTouchMove(id,x,y)/
            #     OnTouchEnd(id,x,y)/OnTouchCancel(id)（AIP 书籍触摸版 aipScroller 实证，
            #     简易存储 terminal_invslot 同签名）：OnTouchMove 的 x/y 参数直接给实时
            #     坐标（无 lasty 依赖），手指位移 dy → _target_offset 跟手（浮点，
            #     OnUpdate 平滑消费）。_fw_listtouch 防重复；self 是列表祖先（触摸分发
            #     必经），无需 black 垫层（LOL 副本无 black）。
            if 'self._fw_listtouch' not in text1:
                touch_new = (
                    '    -- 柠版适配: 列表本体触摸拖动(OnTouch 原生通道, 手工版 ScrollingGrid 同款: 划列表内容直接滚动) v1.4.15\n'
                    '    -- v1.4.17: 滑块区域分流——起点落在滑块(marker)上 → 滑块语义(拖上→view_offset 减小→看上面);\n'
                    '    --           否则列表语义(划上→view_offset 增大→看下面)。两语义符号相反,\n'
                    '    --           单一符号必然反一方(用户实测: 列表覆盖滑块 → 滑块被列表通道接管 → 反)\n'
                    '    if self._fw_listtouch == nil then\n'
                    '        self._fw_listtouch = true\n'
                    '        self._lt_id = nil\n'
                    '        self._lt_y = nil\n'
                    '        self._fw_on_slider = nil\n'
                    '        local __LT_G = GLOBAL\n'
                    '        function self:OnTouchStart(id, x, y)\n'
                    '            if self._lt_id == nil then\n'
                    '                self._lt_id = id\n'
                    '                self._lt_y = y\n'
                    '                self._fw_on_slider = false\n'
                    '                local mk = self.position_marker\n'
                    '                if mk then\n'
                    '                    local mx, my = mk:GetWorldPosition():Get()\n'
                    '                    if math.abs(x - mx) <= 50 and math.abs(y - my) <= 50 then\n'
                    '                        self._fw_on_slider = true\n'
                    '                    end\n'
                    '                end\n'
                    '                if __LT_G.TheFrontEnd then __LT_G.TheFrontEnd:LockFocus(true, id) end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function self:OnTouchMove(id, x, y)\n'
                    '            if self._lt_id == id and self._lt_y ~= nil then\n'
                    '                local dy = y - self._lt_y\n'
                    '                self._lt_y = y\n'
                    '                if dy ~= 0 then\n'
                    '                    if self._fw_on_slider then\n'
                    '                        -- 滑块语义: 拖上(dy>0) → view_offset 减小 → marker 上移 → 看上面\n'
                    '                        -- v1.4.18: 除以 scroll_bar_container 竖向缩放(sf)——marker 在缩放\n'
                    '                        --   容器内, 屏幕位移 = 局部位移×sf; 不除则滑块比手指快 sf 倍\n'
                    '                        local step = self.step_size or 40\n'
                    '                        local sf = 1\n'
                    '                        if self.scroll_bar_container then\n'
                    '                            local ok, sx, sy = pcall(function() return self.scroll_bar_container:GetScale():Get() end)\n'
                    '                            if ok and sy then sf = sy or 1 end\n'
                    '                        end\n'
                    '                        if step > 0 and sf > 0 then\n'
                    '                            self._target_offset = math.clamp((self._target_offset or self.view_offset) - dy / step / sf, 0, self.max_step or 0)\n'
                    '                            self._fw_dragging = true\n'
                    '                            self:StartUpdating()\n'
                    '                        end\n'
                    '                    else\n'
                    '                        -- 列表语义: 划上(dy>0) → view_offset 增大 → 看下面(内容跟随手指)\n'
                    '                        local step = (self.item_height or 60) + (self.item_padding or 0)\n'
                    '                        if step > 0 then\n'
                    '                            self._target_offset = math.clamp((self._target_offset or self.view_offset) + dy / step, 0, self.max_step or 0)\n'
                    '                            self._fw_dragging = true\n'
                    '                            self:StartUpdating()\n'
                    '                        end\n'
                    '                    end\n'
                    '                end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function self:OnTouchEnd(id, x, y)\n'
                    '            if self._lt_id == id then\n'
                    '                self._lt_id = nil\n'
                    '                self._lt_y = nil\n'
                    '                self._fw_on_slider = nil\n'
                    '                self._fw_dragging = nil\n'
                    '                if __LT_G.TheFrontEnd then __LT_G.TheFrontEnd:LockFocus(false, id) end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function self:OnTouchCancel(id)\n'
                    '            if self._lt_id == id then\n'
                    '                self._lt_id = nil\n'
                    '                self._lt_y = nil\n'
                    '                self._fw_on_slider = nil\n'
                    '                if __LT_G.TheFrontEnd then __LT_G.TheFrontEnd:LockFocus(false, id) end\n'
                    '            end\n'
                    '        end\n'
                    '    end\n'
                    '    -- 柠版适配: 滑块 marker 触摸拖动(跟手无坐标换算, 无反馈振荡) v1.4.15\n'
                    '    --           拖动滑块闪烁根因 = SetWhileDown→DoDragScroll 读 marker 世界\n'
                    '    --           位置做换算, 而 OnUpdate 每帧移动 marker → 反馈循环振荡;\n'
                    '    --           改为 marker 自身 OnTouch: 手指位移 dy → _target_offset 直接\n'
                    '    --           跟手(读 step_size 滑轨步长, 不读 marker 位置), 无振荡\n'
                    '    if self.position_marker and self.position_marker._fw_mk_touch == nil then\n'
                    '        local mk = self.position_marker\n'
                    '        mk._fw_mk_touch = true\n'
                    '        mk._mk_id = nil\n'
                    '        mk._mk_y = nil\n'
                    '        mk._mk_active = nil\n'
                    '        local __MK_G = GLOBAL\n'
                    '        local __MK_LIST = self\n'
                    '        function mk:OnTouchStart(id, x, y)\n'
                    '            if self._mk_id == nil then\n'
                    '                self._mk_id = id\n'
                    '                self._mk_y = y\n'
                    '                self._mk_active = true\n'
                    '                if __MK_G.TheFrontEnd then __MK_G.TheFrontEnd:LockFocus(true, id) end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function mk:OnTouchMove(id, x, y)\n'
                    '            if self._mk_id == id and self._mk_y ~= nil then\n'
                    '                local dy = y - self._mk_y\n'
                    '                self._mk_y = y\n'
                    '                if dy ~= 0 then\n'
                    '                    local p = __MK_LIST\n'
                    '                    local step = p.step_size or 40\n'
                    '                    -- v1.4.18: 除以容器竖向缩放(sf)——marker 在 SetScale(1,sf) 容器内,\n'
                    '                    --   屏幕位移=局部位移×sf; 不除则滑块比手指快 sf 倍(用户实测"比手快")\n'
                    '                    local sf = 1\n'
                    '                    if p.scroll_bar_container then\n'
                    '                        local ok, sx, sy = pcall(function() return p.scroll_bar_container:GetScale():Get() end)\n'
                    '                        if ok and sy then sf = sy or 1 end\n'
                    '                    end\n'
                    '                    if step > 0 and sf > 0 then\n'
                    '                        -- v1.4.17: 滑块语义 -dy/step: 拖上(dy>0) → view_offset 减小 → marker 上移 → 看上面\n'
                    '                        p._target_offset = math.clamp((p._target_offset or p.view_offset) - dy / step / sf, 0, p.max_step or 0)\n'
                    '                        p._fw_dragging = true\n'
                    '                        p:StartUpdating()\n'
                    '                    end\n'
                    '                end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function mk:OnTouchEnd(id, x, y)\n'
                    '            if self._mk_id == id then\n'
                    '                self._mk_id = nil\n'
                    '                self._mk_y = nil\n'
                    '                self._mk_active = nil\n'
                    '                __MK_LIST._fw_dragging = nil\n'
                    '                if __MK_G.TheFrontEnd then __MK_G.TheFrontEnd:LockFocus(false, id) end\n'
                    '                return true\n'
                    '            end\n'
                    '            return false\n'
                    '        end\n'
                    '        function mk:OnTouchCancel(id)\n'
                    '            if self._mk_id == id then\n'
                    '                self._mk_id = nil\n'
                    '                self._mk_y = nil\n'
                    '                self._mk_active = nil\n'
                    '                __MK_LIST._fw_dragging = nil\n'
                    '                if __MK_G.TheFrontEnd then __MK_G.TheFrontEnd:LockFocus(false, id) end\n'
                    '            end\n'
                    '        end\n'
                    '    end\n'
                )
                anchor5 = None
                for m5 in re.finditer(r'self:StartUpdating\(\)\s*\n', text1):
                    anchor5 = m5
                if anchor5:
                    text1 = text1[:anchor5.end()] + touch_new + text1[anchor5.end():]
                    changed = True

            # a4) content_root 整体平移模型（手工版同构，★滑动闪烁根因修复 v1.4.8）：
            #     原版 RefreshView 每帧按 item_offset 槽位重排所有条目位置 + 显隐切换 →
            #     连续滚动时每帧跳变 = 闪烁。手工版 = ctor 建 content_root 平移层，
            #     条目布局固定，滚动 = content_root:SetPosition 整体平移（平滑连续，无闪烁）。
            #     1) ctor 内最后一个 self.items = 赋值后创建 content_root（循环外）
            #     2) items 挂载 self:AddChild(v) → content_root:AddChild(v)
            #     ★ v1.4.10 限定条件：仅"分组式列表"（含 scroll_page_member）才注入平移模型——
            #     手工版只重写 pedia（分组列表），common/pedia_items 保持原版槽位式（柠版实测正常）；
            #     对普通列表注入平移反而可能闪（LOL 右侧 common 实证）。
            if 'self.content_root' not in text1 and 'scroll_page_member' in text:
                # 限定 ctor 范围：local <cls> = Class(Widget, function(self, ...) 到 ctor 函数 end)
                # 避免误取方法里的 self.items = （LOL pedia 560/626 行切页/重置方法实证）
                ctor_m = re.search(
                    r'local\s+%s\s*=\s*Class\([^)]*,\s*function\(self' % re.escape(cls), text1)
                if ctor_m:
                    lines_c = text1.split('\n')
                    sline_c = text1[:ctor_m.start()].count('\n')
                    dep_c = 0
                    eline_c = None
                    for j in range(sline_c, len(lines_c)):
                        l = lines_c[j]
                        dep_c += l.count('function') + (l.count('if ') - l.count('elseif ')) + l.count('for ') + l.count('while ')
                        dep_c -= l.count('end')
                        if dep_c <= 0 and l.strip().endswith('end)') and j > sline_c:
                            eline_c = j
                            break
                    if eline_c is not None:
                        line_starts_c = []
                        acc_c = 0
                        for l in lines_c:
                            line_starts_c.append(acc_c)
                            acc_c += len(l) + 1
                        ctor_end_off = line_starts_c[eline_c] + len(lines_c[eline_c])
                        ctor_sub = text1[ctor_m.start():ctor_end_off]
                        items_assigns = [mm.start() + ctor_m.start()
                                         for mm in re.finditer(r'^\s*self\.items\s*=', ctor_sub, re.M)]
                        if items_assigns:
                            pos = items_assigns[-1]
                            nl = text1.find('\n', pos)
                            text1 = (text1[:nl + 1] +
                                     '    self.content_root = self:AddChild(Widget(\'content_root\'))\n' +
                                     text1[nl + 1:])
                            # items 挂载改道（行级，避免误伤注释；CRLF 兼容）
                            text1 = re.sub(
                                r'^(\s*)self:AddChild\(v\)\r?$',
                                r'\1self.content_root:AddChild(v)',
                                text1, flags=re.M)
                            changed = True

            # b) Scroll 开头注入 _target_offset = nil
            pat_scroll = re.compile(
                r'(function\s+%s:Scroll\([^)]*\)\s*\n)(\s*)local\s+prev\s*=\s*self\.view_offset'
                % re.escape(cls))
            m2 = pat_scroll.search(text1)
            if m2:
                repl = (m2.group(1) + m2.group(2) + 'self._target_offset = nil\n'
                        + m2.group(2) + 'local prev = self.view_offset')
                text1 = text1[:m2.start()] + repl + text1[m2.end():]
                changed = True

            # c) DoDragScroll 函数体重写（深度计数定位函数边界）
            m3 = re.search(r'function\s+%s:DoDragScroll\(\)\s*\n' % re.escape(cls), text1)
            if m3:
                lines2 = text1.split('\n')
                start_line = text1[:m3.start()].count('\n')
                depth = 0
                end_line = None
                for j in range(start_line, len(lines2)):
                    l = lines2[j]
                    depth += l.count('function') + (l.count('if ') - l.count('elseif ')) + l.count('for ') + l.count('while ')
                    depth -= l.count('end')
                    if depth <= 0 and 'end' in l and j > start_line:
                        end_line = j
                        break
                if end_line is not None:
                    new_body = (
                        '    -- 柠版适配: 拖动换算 = 手指屏幕 y 直接映射到滑轨(不临时移动手柄,\n'
                        '    -- 避免触屏下位置跳变振荡; 只设目标步数由 OnUpdate 每帧平滑靠近)\n'
                        '    -- v1.4.16/17: 换算基准用按下时记录的 marker 位置(固定, 拖动中不更新)\n'
                        '    --   → 消除 OnUpdate 每帧移动 marker 造成的反馈振荡("固定中间闪烁"根因);\n'
                        '    --   方向: TheFrontEnd.lasty 屏幕系(下正), marker 世界/局部上正, 减法后\n'
                        '    --   方向自洽——手指上滑(lasty 减小)→ ratio 减小 → view_offset 减小\n'
                        '    --   → marker 上移(看更上面)。v1.4.16 曾取反 1- 导致方向反, v1.4.17 恢复\n'
                        '    local marker = self.position_marker\n'
                        '    local mpos = marker:GetPosition()\n'
                        '    local marker_wx = marker:GetWorldPosition().x\n'
                        '    local marker_wy = self._drag_marker_wy or marker:GetWorldPosition().y\n'
                        '    local marker_ly = self._drag_marker_ly or mpos.y\n'
                        '    local lastx = TheFrontEnd.lastx or self._drag_lastx or marker_wx\n'
                        '    local lasty = TheFrontEnd.lasty or self._drag_lasty or marker_wy\n'
                        '    if math.abs(lastx - marker_wx) <= DRAG_SCROLL_X_THRESHOLD then\n'
                        '        local local_offset = marker_wy - marker_ly\n'
                        '        local local_y = lasty - local_offset\n'
                        '        local slide_start = self.height/2 - arrow_button_size\n'
                        '        local slide_range = self.height - 2*arrow_button_size\n'
                        '        local bottom_y = slide_start - slide_range\n'
                        '        -- v1.4.18: 滑轨屏幕范围 = slide_range × sf(container 竖向缩放), 不除则滑块比手快 sf 倍\n'
                        '        local sf = 1\n'
                        '        if self.scroll_bar_container then\n'
                        '            local ok, sx, sy = pcall(function() return self.scroll_bar_container:GetScale():Get() end)\n'
                        '            if ok and sy then sf = sy or 1 end\n'
                        '        end\n'
                        '        local scroll_value = math.clamp( (local_y - bottom_y) / (slide_range * sf), 0, 1 )\n'
                        '        self:ScrollToRatio(scroll_value)\n'
                        '    else\n'
                        '        self:MoveMarkerToNearestStep()\n'
                        '    end\n'
                        'end\n')
                    line_starts = []
                    acc = 0
                    for l in lines2:
                        line_starts.append(acc)
                        acc += len(l) + 1
                    end_start = line_starts[end_line]
                    end_len = len(lines2[end_line])
                    text1 = text1[:m3.end()] + new_body + text1[end_start + end_len:]
                    changed = True

            # c2) RefreshView 函数体重写（content_root 平移模型，手工版同构，无闪烁）
            #     ★ v1.4.10 与 a4 同条件：仅分组式列表（scroll_page_member）重写平移；
            #     普通列表（common/pedia_items）保持原版槽位式（手工版实证柠版正常）
            if 'scroll_page_member' in text1 and '-- 柠版适配: 连续平移滚动(手工版同构)' not in text1:
                m_rv = re.search(
                    r'function\s+%s:RefreshView\(movemarker\)\s*\n' % re.escape(cls), text1)
                if m_rv:
                    lines3 = text1.split('\n')
                    start_line3 = text1[:m_rv.start()].count('\n')
                    depth3 = 0
                    end_line3 = None
                    for j in range(start_line3, len(lines3)):
                        l = lines3[j]
                        depth3 += l.count('function') + (l.count('if ') - l.count('elseif ')) + l.count('for ') + l.count('while ')
                        depth3 -= l.count('end')
                        if depth3 <= 0 and 'end' in l and j > start_line3:
                            end_line3 = j
                            break
                    if end_line3 is not None:
                        new_rv = (
                            '    -- 柠版适配: 连续平移滚动(手工版同构): 条目布局固定, content_root 整体平移,\n'
                            '    -- 条目位置随滚动连续变化(非槽位跳变), 视口外条目 Hide(无每帧显隐切换, 无闪烁)\n'
                            '    local nextYPos = self.height/2 - (arrow_button_size * .5) + self.yInitial\n'
                            '    local step = self.item_height + self.item_padding\n'
                            '    if self.content_root then\n'
                            '        self.content_root:SetPosition(0, self.view_offset * step)\n'
                            '    end\n'
                            '    if self.updatefn == nil and self.static_widgets == nil then\n'
                            '        -- 柠版适配 v1.4.14/16: 首次(或换组)布局固定 items 相对 content_root 的位置\n'
                            '        -- 并全量裁剪(视口外 Hide)——只 SetPosition 不裁剪会让首屏外 items\n'
                            '        -- 保持 Show 显示到底板外(v1.4.16 溢出修复); 之后 content_root 整体平移\n'
                            '        if not self._fw_items_laid or self._fw_items_ref ~= self.items then\n'
                            '            self._fw_items_laid = true\n'
                            '            self._fw_items_ref = self.items\n'
                            '            local half = self.height/2\n'
                            '            for i, v in ipairs(self.items) do\n'
                            '                v:SetPosition(-self.width/2 + self.x_offset, nextYPos - ((i-1) * step))\n'
                            '                local y = nextYPos - ((i-1) * step) + self.view_offset * step\n'
                            '                if y > half or y < -half then\n'
                            '                    v:Hide()\n'
                            '                else\n'
                            '                    v:Show()\n'
                            '                end\n'
                            '            end\n'
                            '        end\n'
                            '        -- 视口裁剪只遍历边界附近 items(其余显隐不变), 避免每步全量 Show/Hide 掉帧\n'
                            '        local half = self.height/2\n'
                            '        local first = math.max(1, math.floor(self.view_offset))\n'
                            '        local last = math.min(#self.items, math.floor(self.view_offset) + self.widgets_per_view + 2)\n'
                            '        for i = first, last do\n'
                            '            local v = self.items[i]\n'
                            '            local y = nextYPos - ((i-1) * step) + self.view_offset * step\n'
                            '            if y > half or y < -half then\n'
                            '                v:Hide()\n'
                            '            else\n'
                            '                v:Show()\n'
                            '            end\n'
                            '        end\n'
                            '    elseif self.updatefn ~= nil and self.static_widgets ~= nil then\n'
                            '        local numShown = 0\n'
                            '        for i,v in ipairs(self.items) do\n'
                            '            local item_offset = (self.view_offset+1) - i\n'
                            '            if item_offset <= 0 and numShown < self.widgets_per_view then\n'
                            '                if self.static_widgets[i - self.view_offset] then\n'
                            '                    self.updatefn(self.static_widgets[i - self.view_offset], v, i)\n'
                            '                    self.static_widgets[i - self.view_offset]:SetPosition(-self.width/2 + self.x_offset, nextYPos + (step * item_offset))\n'
                            '                end\n'
                            '                numShown = numShown + 1\n'
                            '            end\n'
                            '        end\n'
                            '        for i, v in ipairs(self.static_widgets) do\n'
                            '            if i <= #self.items then v:Show() else v:Hide() end\n'
                            '        end\n'
                            '    end\n'
                            '    if #self.items <= self.widgets_per_view then\n'
                            '        self.up_button:Hide()\n'
                            '        self.down_button:Hide()\n'
                            '        self.position_marker:Hide()\n'
                            '        self.scroll_bar:Hide()\n'
                            '        self.scroll_bar_line:Hide()\n'
                            '    else\n'
                            '        self.up_button:Show()\n'
                            '        self.down_button:Show()\n'
                            '        self.position_marker:Show()\n'
                            '        self.scroll_bar:Show()\n'
                            '        self.scroll_bar_line:Show()\n'
                            '    end\n'
                            '    if movemarker then\n'
                            '        local marker = self.position_marker:GetPosition()\n'
                            '        local newY = (self.height/2 - arrow_button_size) - (self.view_offset * self.step_size)\n'
                            '        if newY < -self.height/2 + arrow_button_size then\n'
                            '            newY = -self.height/2 + arrow_button_size\n'
                            '        elseif newY > self.height/2 - arrow_button_size then\n'
                            '            newY = self.height/2 - arrow_button_size\n'
                            '        end\n'
                            '        self.position_marker:SetPosition(marker.x, newY)\n'
                            '    end\n'
                            'end\n')
                        line_starts3 = []
                        acc3 = 0
                        for l in lines3:
                            line_starts3.append(acc3)
                            acc3 += len(l) + 1
                        end_start3 = line_starts3[end_line3]
                        end_len3 = len(lines3[end_line3])
                        text1 = (text1[:m_rv.end()] + new_rv +
                                 text1[end_start3 + end_len3:])
                        changed = True

            # d/e) ScrollToRatio + OnUpdate 注入（缺失才注入，插在 return <cls> 前）
            rm = re.search(r'\nreturn\s+%s\b' % re.escape(cls), text1)
            extra = ''
            if (':%s:ScrollToRatio' % cls) not in text1:
                extra += (
                    '\nfunction %s:ScrollToRatio(ratio)\n'
                    '    self._target_offset = math.clamp(ratio * self.max_step, 0, self.max_step)\n'
                    'end\n' % cls)
            if (':%s:OnUpdate' % cls) not in text1:
                extra += (
                    '\nfunction %s:OnUpdate(dt)\n'
                    '    -- 柠版适配: 浮点逼近目标步数(每帧 20%% 剩余距离), 内容+滑块全程平滑无闪烁\n'
                    '    --           (整数步 = 每帧跳一步(item 高度约 60px), 触屏下视觉闪烁——LOL 图鉴实测;\n'
                    '    --           手工版改用 ScrollingGrid 原生平滑, 此处等价实现)\n'
                    '    -- v1.4.12: 平移模型每帧仅轻量 SetPosition 容器; 跨整步才 RefreshView\n'
                    '    --           (显隐/槽位跳变), marker 每帧浮点平滑——避免全量遍历每帧重绘掉帧\n'
                    '    if self._target_offset ~= nil then\n'
                    '        local prev = self.view_offset\n'
                    '        local diff = self._target_offset - self.view_offset\n'
                    '        if self._fw_dragging then\n'
                    '            -- v1.4.21: 拖动中 1:1 直接跟手(手工版 ScrollingGrid 行为),\n'
                    '            --           不指数逼近——快拖时每帧增量大, 逼近滞后=滑块比手慢\n'
                    '            self.view_offset = self._target_offset\n'
                    '        elseif math.abs(diff) < 0.1 then\n'
                    '            self.view_offset = self._target_offset\n'
                    '            self._target_offset = nil\n'
                    '        else\n'
                    '            self.view_offset = self.view_offset + diff * math.min(1, dt * 20)\n'
                    '        end\n'
                    '        if self.content_root then\n'
                    '            self.content_root:SetPosition(0, self.view_offset * (self.item_height + self.item_padding))\n'
                    '        end\n'
                    '        if math.floor(prev) ~= math.floor(self.view_offset) then\n'
                    '            self:RefreshView()\n'
                    '        end\n'
                    '        self:MoveMarkerToNearestStep()\n'
                    '    end\n'
                    'end\n' % cls)
            if extra:
                if rm:
                    pos = rm.start()
                    text1 = text1[:pos] + extra.rstrip() + '\n' + text1[pos:]
                else:
                    text1 = text1.rstrip() + '\n' + extra

            if changed or extra:
                text1 = text1.rstrip() + '\n-- __fw_drag_rewrite v1.4.5\n'
                out = text1.encode('utf-8')
                if raw.startswith(b'\xef\xbb\xbf'):
                    out = b'\xef\xbb\xbf' + out
                open(p, 'wb').write(out)
                n += 1
    return n


def inject_touch_scroll_files(target):
    """★ 直接改滚动类文件（不动 modmain）——AIP §20.15.2 实测 modmain require 路线
    在柠版有卡加载风险（双括号 bug 修复后 require(string) 仍可能因 mod require 路径/
    加载时机问题卡加载页）。此路线在滚动类文件内注入 EnableTouchScroll + ctor 包装，
    与手工书籍触摸版同构，加载时机安全（类文件由 mod 自身 modimport 加载，注入块
    只是给类加方法 + 包装 ctor，实例化时才生效）。返回注入的类数量。"""
    base = os.path.join(target, 'scripts')
    if not os.path.isdir(base):
        return 0
    markers = ('CONTROL_SCROLLBACK', 'CONTROL_SCROLLFWD',
               'ScrollByPixels', 'SetScrollable')
    n = 0
    for r, dirs, files in os.walk(base):
        if 'mods' in r.split(os.sep):
            continue
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
                text = raw.decode('utf-8-sig', errors='replace')
            except Exception:
                continue
            if '__fw_ts_installed' in text:
                continue  # 已注入过（幂等）
            if not any(m in text for m in markers):
                continue
            # ★ ScrollableList 系（标准 position_marker 拖动 + DoDragScroll）跳过注入：
            #   框架原生触摸已支持 marker 拖动（手工版 LOL 零触摸注入、完美滑动实证——
            #   SetOnDown/SetWhileDown→DoDragScroll 走鼠标事件通道，仅需 lastx 兜底，
            #   已由防御性修复 c 段注入）。注入自定义 OnTouchMove→Scroll(步数)→全量
            #   RefreshView 反而与原生拖动双通道冲突 → 列表来回跳闪烁（LOL v13 实测）。
            #   仅无 marker 拖动结构的滚动类（如 AIP aipScroller）才注入自定义触摸。
            if 'DoDragScroll' in text and 'position_marker' in text:
                continue
            if 'Class(' not in text:
                continue
            m = re.search(r'local\s+(\w+)\s*=\s*Class\(', text)
            if not m:
                continue
            cls = m.group(1)
            # 在 return <cls> 前插入；找不到 return 则文件末尾（无 return 的文件仍可执行尾部代码）
            rm = re.search(r'\nreturn\s+%s\b' % re.escape(cls), text)
            block = TOUCH_SCROLL_FILE_BLOCK.replace('%CLASS%', cls)
            if rm:
                pos = rm.start()
                out = text[:pos] + '\n' + block.rstrip() + '\n' + text[pos:]
            else:
                out = text.rstrip() + '\n' + block
            out = out.encode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf'):
                out = b'\xef\xbb\xbf' + out
            open(p, 'wb').write(out)
            n += 1
    return n


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

# ===========================================================================
# v1.6.0 P0：编码统一 / worldgen 别名 / 原版图集修正（静态表）/ 图集表重建
# ===========================================================================

def normalize_encoding(root):
    """全量 .lua 统一 UTF-8 BOM + CRLF（柠版加载器格式敏感，更多料理 559 文件实证）。
    幂等：已有 BOM + CRLF 跳过。返回 (补BOM数, 换行归一数, 跳过数)。"""
    bom_n = crlf_n = skip_n = 0
    _NO_BOM = ('sound_banks_auto.lua', 'tile_preload_auto.lua')  # 工具特意无 BOM 的清单
    for r, dirs, files in os.walk(root):
        for f in files:
            if not f.endswith('.lua') or f in _NO_BOM:
                continue
            p = os.path.join(r, f)
            try:
                raw = open(p, 'rb').read()
            except Exception:
                skip_n += 1
                continue
            if b'\x00' in raw:
                skip_n += 1
                continue
            try:
                text = raw.decode('utf-8-sig')
            except Exception:
                skip_n += 1
                continue
            has_bom = raw.startswith(b'\xef\xbb\xbf')
            uni = text.replace('\r\n', '\n').replace('\r', '\n')
            # utf-8-sig 解码已剥 BOM——无条件重加（有 BOM 保留，无 BOM 补），否则会误剥原 BOM
            out = b'\xef\xbb\xbf' + uni.replace('\n', '\r\n').encode('utf-8')
            if not has_bom:
                bom_n += 1
            if out != raw:
                crlf_n += 1
                try:
                    open(p, 'wb').write(out)
                except Exception:
                    skip_n += 1
                    crlf_n -= 1
                    if not has_bom:
                        bom_n -= 1
    return bom_n, crlf_n, skip_n


def inject_worldgen_globals(target):
    """modworldgenmain 链 modimport 文件顶部注入 _G 别名（worldgen 隔离 env 无裸 Lua 内置，
    更多料理 terrain pcall nil 实证）。幂等标记 __FW_WORLDGEN_GLOBALS。返回注入文件数。"""
    wgm = os.path.join(target, 'modworldgenmain.lua')
    if not os.path.exists(wgm):
        return 0
    try:
        t = open(wgm, encoding='utf-8-sig', errors='replace').read()
    except Exception:
        return 0
    imports = re.findall(r'modimport\s*\(\s*["\']([^"\']+)["\']', t)
    builtins = ('pcall', 'type', 'pairs', 'ipairs', 'tostring')
    fixed = 0
    for imp in imports:
        rel = imp + ('.lua' if not imp.endswith('.lua') else '')
        p = os.path.join(target, *rel.split('/'))
        if not os.path.exists(p):
            continue
        try:
            raw = open(p, 'rb').read()
        except Exception:
            continue
        if b'__FW_WORLDGEN_GLOBALS' in raw:
            continue
        text = raw.decode('utf-8-sig', errors='replace')
        need = [n for n in builtins
                if re.search(r'\b%s\b' % n, text)
                and ('local %s = _G.%s' % (n, n)) not in text]
        if not need:
            continue
        head = '-- __FW_WORLDGEN_GLOBALS\r\n' + ''.join('local %s = _G.%s\r\n' % (n, n) for n in need)
        bom = raw.startswith(b'\xef\xbb\xbf')
        new = (head + text).encode('utf-8')
        if bom:
            new = b'\xef\xbb\xbf' + new
        try:
            open(p, 'wb').write(new)
            fixed += 1
        except Exception:
            pass
    return fixed


_ATLAS_TABLE_CANDIDATES = ('vanilla_atlas_jh210.json', 'vanilla_atlas_jh142.json')


def load_vanilla_atlas(explicit=None):
    """读柠版原版图集静态表（region → 柠版图集路径，无子目录）。
    表由 --rebuild-atlas 从 APK images.zip 解析生成。返回 dict 或 None。
    v1.6.2：候选表自动选最新——jh210（2.1.0，6626 region）优先，
    旧 jh142（1.4.2，6187 region）兜底；也支持 --atlas <json> 显式指定。"""
    import json as _json
    if explicit and os.path.isfile(explicit):
        try:
            with open(explicit, encoding='utf-8') as f:
                return _json.load(f)
        except Exception:
            return None
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in _ATLAS_TABLE_CANDIDATES:
        p = os.path.join(here, cand)
        if os.path.isfile(p):
            try:
                with open(p, encoding='utf-8') as f:
                    return _json.load(f)
            except Exception:
                pass
    return None


def scan_vanilla_atlas_recipes(target):
    """扫 .lua 找 recipe 的 image 字段（显式 atlas 优先）。返回 image 去重列表。"""
    pat_img = re.compile(r'image\s*=\s*"([^"]+\.tex)"')
    found = {}
    for r, dirs, files in os.walk(target):
        for f in files:
            if not f.endswith('.lua'):
                continue
            p = os.path.join(r, f)
            try:
                t = open(p, encoding='utf-8-sig', errors='replace').read()
            except Exception:
                continue
            for m in pat_img.finditer(t):
                found.setdefault(m.group(1), 0)
                found[m.group(1)] += 1
    return sorted(found)


def inject_vanilla_atlas_fix(target, modname, fix_map, mk=None):
    """生成 postinit/<modkey>_vanilla_atlas.lua（遍历 AllRecipes 改 recipe.atlas 指柠版原版图集）
    并在 modmain 末尾挂载 modimport。幂等 __FW_VANILLA_ATLAS_FIX。返回命中数。"""
    mk = mk or modkey(modname)
    rel = 'postinit/%s_vanilla_atlas.lua' % mk
    p = os.path.join(target, rel)
    if os.path.exists(p):
        return len(fix_map)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    body = [
        '-- __FW_VANILLA_ATLAS_FIX (generated by dst_mobile_adapter v1.6.0)',
        '-- 柠版原版图集 region 归属修正（更多料理 4 鱼实证：路径无子目录 + region 位置差异）',
        'local FIX = {',
    ]
    for img, atlas in sorted(fix_map.items()):
        body.append('    ["%s"] = "%s",' % (img, atlas))
    body.append('}')
    body.append('local AllRecipes = rawget(_G, "AllRecipes")')
    body.append('if type(AllRecipes) == "table" then')
    body.append('    for _, r in pairs(AllRecipes) do')
    body.append('        if type(r) == "table" and FIX[r.image] then r.atlas = FIX[r.image] end')
    body.append('    end')
    body.append('end')
    write_new_lua(p, '\r\n'.join(body) + '\r\n')
    # modmain 末尾挂载（幂等）
    mm = os.path.join(target, 'modmain.lua')
    if os.path.isfile(mm):
        raw = open(mm, 'rb').read()
        if b'__FW_VANILLA_ATLAS_FIX' not in raw and ('%s_vanilla_atlas.lua' % mk).encode('utf-8') not in raw:
            text = raw.decode('utf-8-sig', errors='replace')
            bom = raw.startswith(b'\xef\xbb\xbf')
            block = '\r\n-- 柠版原版图集修正（v1.6.0）\r\nmodimport("%s")\r\n' % rel
            new = (text.rstrip() + '\r\n' + block).encode('utf-8')
            if bom:
                new = b'\xef\xbb\xbf' + new
            open(mm, 'wb').write(new)
    return len(fix_map)


def rebuild_atlas_table(apk_path):
    """从柠版 APK 解析 images.zip 全部 xml → 生成 vanilla_atlas_<版本>.json。返回输出路径或 None。"""
    import json as _json
    import time as _time
    if not apk_path or not os.path.isfile(apk_path):
        print('[错误] --rebuild-atlas 需要 --apk <柠版APK路径>')
        return None
    ver = os.path.basename(apk_path).replace('.apk', '').replace('(', '').replace(')', '')
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, 'vanilla_atlas_%s.json' % ver)
    try:
        with zipfile.ZipFile(apk_path) as z:
            cand = [n for n in z.namelist() if n.endswith('images.zip') and 'databundles' in n]
            if not cand:
                print('[错误] APK 中未找到 assets/databundles/images.zip')
                return None
            data = z.read(cand[0])
        iz = zipfile.ZipFile(io.BytesIO(data))
        xmls = sorted(n for n in iz.namelist() if n.endswith('.xml'))
        re_el = re.compile(r'<Element\s+name="([^"]+)"')
        atlas_list = []
        region_to_atlas = {}
        multi = {}
        for x in xmls:
            txt = iz.read(x).decode('utf-8', errors='replace')
            atlas_list.append(x)
            for r in re_el.findall(txt):
                if r in region_to_atlas:
                    multi.setdefault(r, []).append(region_to_atlas[r])
                    multi[r].append(x)
                else:
                    region_to_atlas[r] = x
        out = {
            'source_apk': os.path.basename(apk_path),
            'generated': _time.strftime('%Y-%m-%d'),
            'atlas_count': len(xmls),
            'region_count': len(region_to_atlas),
            'conflict_regions': multi,
            'atlas_list': atlas_list,
            'region_to_atlas': region_to_atlas,
        }
        with open(out_path, 'w', encoding='utf-8') as f:
            _json.dump(out, f, ensure_ascii=False)
        print('== 图集表重建: %s（%d 图集 / %d region）' % (out_path, len(xmls), len(region_to_atlas)))
        return out_path
    except Exception as e:
        print('[错误] 图集表重建失败: %s' % e)
        return None


def check_cancel():
    """阶段间取消检查点：置 _CANCEL 后抛 SystemExit(130)，GUI 显示已取消。"""
    if _CANCEL:
        print('== 已取消')
        raise SystemExit(130)


# ---------------------------------------------------------------------------
# v1.6.7：自动文件自检（--verify-auto）/ 只刷自动文件（--sync-auto）/
#         开发者残留清理（--prune-dev）
# ---------------------------------------------------------------------------
def _read_lua(path):
    return open(path, 'rb').read().decode('utf-8-sig', errors='replace')


def verify_auto_files(modroot, modname=None, deep=False, verbose=True, check_folder=True):
    """体检自动文件与 anim/ 资源的一致性。

    存在意义（2026-10-28 泰拉实例）：`early_prefab_auto.lua` 是**生成时刻 anim/ 的
    快照**，框架不会自己发现新资源。资源增删后不重跑适配，就会得两种病：
      ① 新增 zip 未注册 → build 不在内存 → 世界内动画空白（泰拉漏 6 个：staffmeteor /
         lavaarena_fire_fx / lavaarena_heal_projectile / lavaarena_firestaff_meteor /
         meteor_shadow / warning_shadow，全是 prefab 里 Asset("ANIM") 显式声明过的）；
      ② 删了 zip 但条目还在 → 注册期 resolvefilepath 失败 + 白占 FW_EARLY_HOLDER 槽位。
    返回 (errors, warns)。
    """
    errors, warns = [], []
    modroot = os.path.abspath(modroot)
    folder = os.path.basename(modroot.rstrip('/\\'))
    if modname is None:
        modname = folder
    prefix = 'scripts/mods/%s/' % modname
    if check_folder and modname != folder:
        errors.append('目录名 %r ≠ 自动文件 modname %r —— 装进 mods 目录必须同名，'
                      '否则 scripts/mods/ 前缀全失配（invalid asset alias owner）' % (folder, modname))

    anim_dir = os.path.join(modroot, 'anim')
    zips = set(list_anim_zips(modroot)) if os.path.isdir(anim_dir) else set()

    def _rel_ok(path):
        return path.startswith(prefix) and os.path.exists(os.path.join(modroot, path[len(prefix):]))

    # ① early_prefab_auto.lua —— 动画唯一有效通道，漏一条就空一片
    ep = os.path.join(modroot, 'early_prefab_auto.lua')
    if zips and not os.path.exists(ep):
        errors.append('early_prefab_auto.lua 不存在，但 anim/ 有 %d 个 zip —— 全部 build 都不会预注册' % len(zips))
    if os.path.exists(ep):
        txt = _read_lua(ep)
        names = re.findall(r'name\s*=\s*"([^"]+)"', txt)
        paths = re.findall(r'anim\s*=\s*"([^"]+)"', txt)
        dang = [p for p in paths if not _rel_ok(p)]
        if dang:
            errors.append('early_prefab_auto.lua 有 %d 条指向不存在的 anim zip（前 3: %s）'
                          % (len(dang), ', '.join(dang[:3])))
        if zips:
            registered = {n + '.zip' for n in names}
            missing = sorted(zips - registered)
            if missing:
                errors.append('early_prefab_auto.lua 漏注册 %d 个 build（世界内动画会空白；'
                              '跑 --sync-auto 重建即可）: %s%s'
                              % (len(missing), ', '.join(missing[:6]), ' …' if len(missing) > 6 else ''))
            extra = sorted(registered - zips)
            if extra:
                warns.append('early_prefab_auto.lua 有 %d 条对应 zip 已不在 anim/: %s%s'
                             % (len(extra), ', '.join(extra[:4]), ' …' if len(extra) > 4 else ''))
        if len(names) != len(paths):
            warns.append('early_prefab_auto.lua name(%d) 与 anim(%d) 条目数不一致（有缺字段的行）'
                         % (len(names), len(paths)))

    # ② mod_auto.lua —— 四段契约 + entrypoints 与真实文件一致
    ma = os.path.join(modroot, 'mod_auto.lua')
    if not os.path.exists(ma):
        errors.append('mod_auto.lua 不存在（四段契约缺失：entrypoints / asset_case_aliases / '
                      'identity_aliases / autotest_suite）')
    else:
        txt = _read_lua(ma)
        for sec in ('entrypoints', 'asset_case_aliases', 'identity_aliases', 'autotest_suite'):
            if not re.search(r'^\s*%s\s*=\s*\{' % sec, txt, re.M):
                warns.append('mod_auto.lua 缺少 %s 段（212 个官方 mod 全部四段齐全）' % sec)
        dang = sorted({p for p in re.findall(r'"([^"]+)"', txt)
                       if p.startswith(prefix) and not os.path.exists(os.path.join(modroot, p[len(prefix):]))})
        if dang:
            errors.append('mod_auto.lua 有 %d 条指向不存在的文件（前 3: %s）' % (len(dang), ', '.join(dang[:3])))
        wg = re.search(r'\[\s*"modworldgenmain\.lua"\s*\]\s*=\s*(true|false)', txt)
        has_wg = os.path.exists(os.path.join(modroot, 'modworldgenmain.lua'))
        if has_wg and wg and wg.group(1) == 'false':
            errors.append('mod_auto.lua entrypoints["modworldgenmain.lua"]=false —— '
                          '世界生成脚本整段不执行（自定义地形/岛屿静默不生成）')
        if not has_wg and wg and wg.group(1) == 'true':
            warns.append('entrypoints["modworldgenmain.lua"]=true 但文件不存在')

    # ③ preload_assets_auto.lua —— 框架清单只吃 .xml
    pa = os.path.join(modroot, 'preload_assets_auto.lua')
    if os.path.exists(pa):
        txt = _read_lua(pa)
        items = re.findall(r'"([^"]+)"', txt)
        nonxml = [x for x in items if not x.lower().endswith('.xml')]
        if nonxml:
            warns.append('preload_assets_auto.lua 有 %d 条非 .xml（框架 lazy_atlas 会静默丢弃）: %s'
                         % (len(nonxml), ', '.join(nonxml[:3])))
        dang = [x for x in items if not _rel_ok(x)]
        if dang:
            errors.append('preload_assets_auto.lua 有 %d 条指向不存在的文件（前 3: %s）'
                          % (len(dang), ', '.join(dang[:3])))

    # ④ sound_banks_auto.lua —— schema 半对最危险（PreloadMods 直接 false → 整段降级）
    sb = os.path.join(modroot, 'sound_banks_auto.lua')
    if os.path.exists(sb):
        txt = _read_lua(sb)
        for key, pat in (('version', r'version\s*=\s*(\d+)'),
                         ('modname', r'modname\s*=\s*"([^"]*)"'),
                         ('total_bytes', r'total_bytes\s*=\s*(\d+)'),
                         ('pairs', r'pairs\s*=\s*\{')):
            if not re.search(pat, txt):
                errors.append('sound_banks_auto.lua 缺 %s 字段 → 框架 PreloadMods 返回 false，'
                              '五段世界预加载整段降级（动画也一起没了）' % key)
        mname = re.search(r'modname\s*=\s*"([^"]*)"', txt)
        if mname and mname.group(1) != modname:
            errors.append('sound_banks_auto.lua modname=%r ≠ 目录名 %r' % (mname.group(1), modname))
        pairs = re.findall(r'fev\s*=\s*"([^"]+)"\s*,\s*fsb\s*=\s*"([^"]+)"', txt)
        dang = [p for pair in pairs for p in pair if not _rel_ok(p)]
        if dang:
            errors.append('sound_banks_auto.lua 有 %d 条指向不存在的音效文件（前 3: %s）'
                          % (len(dang), ', '.join(dang[:3])))
        mtot = re.search(r'total_bytes\s*=\s*(\d+)', txt)
        if mtot and not dang:
            real = sum(os.path.getsize(os.path.join(modroot, p[len(prefix):]))
                       for pair in pairs for p in pair if _rel_ok(p))
            if int(mtot.group(1)) != real:
                warns.append('sound_banks_auto.lua total_bytes=%s 与实际 %d 不符'
                             '（跑 --sync-auto 重算）' % (mtot.group(1), real))

    # ⑤ tile_preload_auto.lua —— 官方 34 个内置 mod 一个都没有，纯可选
    tp = os.path.join(modroot, 'tile_preload_auto.lua')
    if os.path.exists(tp):
        dang = [x for x in re.findall(r'path\s*=\s*"([^"]+)"', _read_lua(tp)) if not _rel_ok(x)]
        if dang:
            warns.append('tile_preload_auto.lua 有 %d 条指向不存在的文件（前 3: %s）'
                         % (len(dang), ', '.join(dang[:3])))

    # ⑥ 深度检查：只读扫描 anim/ 本身（--verify-auto 才跑，1046 个包约 2 秒）
    if deep and os.path.isdir(anim_dir):
        dev = [f for f in sorted(os.listdir(anim_dir))
               if f.lower().endswith('.zip') and is_dev_anim_zip(f)]
        if dev:
            warns.append('anim/ 下 %d 个美术工具自动备份包（发包不该带，--prune-dev 可清）: %s'
                         % (len(dev), ', '.join(dev[:3])))
        nopay = []
        for f in sorted(os.listdir(anim_dir)):
            if f.lower().endswith('.zip') and not is_dev_anim_zip(f):
                if not anim_zip_has_payload(os.path.join(anim_dir, f)):
                    nopay.append(f)
        if nopay:
            warns.append('anim/ 下 %d 个包既无 build.bin 也无 anim.bin（加载不到任何东西）: %s'
                         % (len(nopay), ', '.join(nopay[:5])))
        nested, dup = [], {}
        for f in sorted(os.listdir(anim_dir)):
            if not f.lower().endswith('.zip'):
                continue
            p = os.path.join(anim_dir, f)
            try:
                with zipfile.ZipFile(p) as z:
                    names = [n for n in z.namelist() if n.lower().endswith('.zip')]
            except Exception as e:
                errors.append('anim/%s 不是合法 zip: %s' % (f, e))
                continue
            if names:
                nested.append('%s 内含 %s' % (f, names[0]))
            if os.path.getsize(p) < 4 * 1024 * 1024:
                h = hashlib.md5(open(p, 'rb').read()).hexdigest()
                dup.setdefault(h, []).append(f)
        if nested:
            warns.append('anim/ 有 %d 个包内嵌 zip（引擎只读 zip 根，嵌层永远加载不到）: %s'
                         % (len(nested), '; '.join(nested[:3])))
        dups = [v for v in dup.values() if len(v) > 1]
        if dups:
            warns.append('anim/ 有 %d 组内容完全相同的 zip: %s'
                         % (len(dups), '; '.join(', '.join(v) for v in dups[:3])))

    if verbose:
        for e in errors:
            print('[ERROR] %s' % e)
        for w in warns:
            print('[WARN ] %s' % w)
        if not errors and not warns:
            print('自动文件体检通过（early=%d 条 / anim=%d 个 zip）。' % (
                len(re.findall(r'name\s*=\s*"', _read_lua(ep))) if os.path.exists(ep) else 0, len(zips)))
    return errors, warns


def read_identity_aliases(path):
    """读取现有 mod_auto.lua 的 identity_aliases（--sync-auto 保留既有工坊 ID 用）。

    为什么需要：identity_aliases 里的 `workshop-xxx` 只有 `--id` 才会写入。
    `--sync-auto` 通常不带 --id，若直接重建就会把它冲掉 → 管理器/存档把同一个 mod
    当成新 mod（配置错挂、重复条目）。
    """
    if not os.path.exists(path):
        return []
    txt = _read_lua(path)
    m = re.search(r'identity_aliases\s*=\s*\{(.*?)\n\s*\}', txt, re.S)
    if not m:
        return []
    return re.findall(r'"([^"]*)"', m.group(1))


def prune_dev_assets(modroot):
    """清除「运行时用不到」的开发者残留（只在适配输出副本上做）。

    只删三类确定无用的东西，其余一律只报告不动手：
      ① `anim/*.autosave.zip` —— 美术工具自动备份；
      ② `sound/source/` —— FMOD Designer 工程源文件（.fdp/.log/.txt + fev/fsb 副本）；
      ③ `sound/**/*.fdp`、`*.log`、`undo-log.txt`。
    """
    removed = []
    anim_dir = os.path.join(modroot, 'anim')
    if os.path.isdir(anim_dir):
        for f in sorted(os.listdir(anim_dir)):
            if f.lower().endswith('.zip') and is_dev_anim_zip(f):
                p = os.path.join(anim_dir, f)
                removed.append(('anim/' + f, os.path.getsize(p)))
                os.remove(p)
    src = os.path.join(modroot, 'sound', 'source')
    if os.path.isdir(src):
        sz = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(src) for x in fs)
        removed.append(('sound/source/', sz))
        shutil.rmtree(src, ignore_errors=True)
    if os.path.isdir(os.path.join(modroot, 'sound')):
        for f in sorted(os.listdir(os.path.join(modroot, 'sound'))):
            if f.lower().endswith(('.fdp', '.log')) or f.lower() == 'undo-log.txt':
                p = os.path.join(modroot, 'sound', f)
                if os.path.isfile(p):
                    removed.append(('sound/' + f, os.path.getsize(p)))
                    os.remove(p)
    return removed


def main():
    ap = argparse.ArgumentParser(description='柠版（手机端 DST）Mod 一键适配工具')
    ap.add_argument('mod', nargs='?', help='Mod 目录或 zip 路径（--rebuild-atlas 时可省略）')
    ap.add_argument('--out', help='输出目录（默认 <输入同级>/<mod名>-柠版适配版）')
    ap.add_argument('--in-place', action='store_true', help='直接处理原目录（默认复制到输出目录）')
    ap.add_argument('--zip', action='store_true', help='处理完打包 zip（内套一层 mod 文件夹）')
    ap.add_argument('--no-tex', action='store_true', help='跳过纹理转换')
    ap.add_argument('--no-compat', action='store_true', help='跳过兼容层生成与 modmain 注入')
    ap.add_argument('--no-autofiles', action='store_true', help='跳过自动文件生成（mod_auto/early_prefab/preload_assets/sound_banks/tile_preload/test）')
    ap.add_argument('--no-rules', action='store_true', help='跳过通用规则（RegisterPrefabs hook + 柠版按钮 FW_RegisterModButton 自动注册）')
    ap.add_argument('--no-postfix', action='store_true', help='跳过 Lua 5.1 兼容 post-fix（unpack(arg)/裸 arg）')
    ap.add_argument('--no-defensive', action='store_true', help='跳过防御性修复（fx/target 判空、lastx/lasty 兜底、items 越界判空）')
    ap.add_argument('--no-scroll', action='store_true', help='跳过滑动/滑块适配（触摸滚动注入 + ScrollableList 拖动重写）')
    ap.add_argument('--no-recipes', action='store_true', help='兼容层不接管 AddRecipe2')
    ap.add_argument('--native', action='store_true',
                    help='纯原生模式（v1.6.0 起默认开启）：不建资源副本、不生成 Assets 全量模块、'
                         '不注入兼容层/FW_ API。只做 解包→纹理ASTC→编码统一→Lua5.1 post-fix→'
                         '自动文件→worldgen 别名→原版图集修正。'
                         '动画靠 early_prefab_auto.lua 全量 build 注册（英雄联盟武器 404 条式，'
                         'AIP §20.14 实证的唯一有效通道）。AIP 17.68MB(兼容层)→9.08MB(native) 全好，'
                         '手工适配成功 mod 均无副本无 FW_——故默认 native')
    ap.add_argument('--legacy-compat', action='store_true',
                    help='（v1.6.0 起默认 native）显式切回旧兼容层模式：资源副本 + mobile_compat '
                         '注入 + RegisterFW/FinishLoad。已实证高风险（AIP 17.68MB 兼容层版本全问题，'
                         'native 9.08MB 全好），仅保留以兼容旧产物复现')
    ap.add_argument('--with-legacy-injects', action='store_true',
                    help='（已废弃，勿用）native 模式额外注入 modmain Assets 表补缺 + '
                         'FW_PreloadAssets——AIP §20.12/§20.13 实证两通道均无效（柠版不读 '
                         'Assets 表 ANIM、FW_PreloadAssets 未生效），仅保留以兼容旧产物复现')
    ap.add_argument('--id', help='手动指定工坊 ID（如 workshop-1085586145）')
    ap.add_argument('--astcenc', help='手动指定 astcenc 可执行文件')
    ap.add_argument('--progress', action='store_true',
                    help='纹理转换阶段逐文件输出 PROGRESS:n/total（GUI 进度条解析用）')
    ap.add_argument('--touch-scroll', action='store_true',
                    help='优化滑块/滑动区域：扫描自定义滚动类（CONTROL_SCROLLBACK / '
                         'SetScrollBound 等特征）并在 modmain 注入柠版触摸滚动'
                         '（OnTouchStart 系列 + SetDragable 双通道，AIP §20.15 三通道方案）')
    ap.add_argument('--workers', type=int, default=0,
                    help='纹理转换并发数（默认 0 = 自动 min(CPU核,6)；大 Mod 内存紧张可调小）')
    ap.add_argument('--no-key-buttons', action='store_true',
                    help='跳过角色按键技能 → 柠版按钮转换（默认自动注册按键技能按钮，'
                         '去重：同 RPC/已有图标按钮不重复注册）')
    ap.add_argument('--simulate-key', action='store_true',
                    help='按键按钮 onpress 优先走 FW_SimulateKey 模拟按键（判空调用，'
                         '默认关闭；FW_SimulateKey 为柠版可选 API，不可用自动回退 RPC）')
    ap.add_argument('--no-lifecycle', action='store_true',
                    help='跳过生命周期任务重写（v1.5.0：DoTaskInTime/DoPeriodicTask 成对 Cancel '
                         '→ FW_DoTaskInTime/FW_DoPeriodicTask/FW_CancelLifecycle 托管，pcall 回退原生）')
    ap.add_argument('--no-touch-pipeline', action='store_true',
                    help='跳过触摸管线兼容注入（v1.5.0：OnTouchLong/OnGesture 补全 + '
                         '__FW_TOUCH_GUARD 防误触/__FW_TOUCH_ENTITIES 屏幕拾取 helper）')
    ap.add_argument('--no-encoding', action='store_true',
                    help='跳过全量 .lua 编码统一（v1.6.0：UTF-8 BOM + CRLF，柠版加载器格式敏感）')
    ap.add_argument('--no-atlas-fix', action='store_true',
                    help='跳过原版图集修正（v1.6.0：读 vanilla_atlas_*.json 静态表，改 recipe.atlas '
                         '指柠版原版图集，更多料理 4 鱼实证）')
    ap.add_argument('--apk', help='柠版 APK 路径：①--rebuild-atlas 时重建图集表；②也可直接指定图集表 json')
    ap.add_argument('--rebuild-atlas', action='store_true',
                    help='重新解析 APK images.zip 生成 vanilla_atlas_<版本>.json（APK 更新时执行一次；'
                         '日常转换直接读表，无需 APK）')
    ap.add_argument('--atlas', help='显式指定图集表 json（v1.6.2：默认自动选最新 jh210>jh142）')
    ap.add_argument('--keep-dead-anims', action='store_true',
                    help='v1.6.4：关闭死动画过滤（默认过滤 anim/ 下源码零引用的 zip，'
                         '防跨 mod asset_case_aliases 撞键 ambiguous）')
    ap.add_argument('--audit-aliases', nargs='+', metavar='PATH',
                    help='v1.6.4：扫描多个已适配 mod（目录或 zip）的 mod_auto.lua，'
                         '报告 asset_case_aliases 跨 mod 撞键（ambiguous 预检），执行后退出')
    ap.add_argument('--sync-auto', action='store_true',
                    help='v1.6.7：只重生成自动文件（mod_auto / early_prefab / preload_assets / '
                         'sound_banks / tile_preload / test），跳过纹理转换、兼容层、通用规则、'
                         'postfix、编码统一、图集修正。资源增删后跑它修「注册表陈旧」；默认原地刷')
    ap.add_argument('--verify-auto', action='store_true',
                    help='v1.6.7：只体检自动文件与 anim/ 一致性（不修改任何文件，深扫 zip），'
                         '有 ERROR 时退出码 1')
    ap.add_argument('--prune-dev', action='store_true',
                    help='v1.6.7：删除运行时用不到的开发者残留（anim/*.autosave.zip、'
                         'sound/source/、*.fdp/*.log），只作用于输出副本')
    args = ap.parse_args()

    # v1.6.7：--sync-auto = 「只刷自动文件」的组合开关（默认原地，避免 130MB 目录再复制一份）
    if args.sync_auto:
        args.native = True
        for k in ('no_tex', 'no_compat', 'no_rules', 'no_postfix', 'no_defensive', 'no_scroll',
                  'no_key_buttons', 'no_lifecycle', 'no_touch_pipeline', 'no_encoding', 'no_atlas_fix'):
            setattr(args, k, True)
        if not args.out:
            args.in_place = True

    # v1.6.7：--verify-auto 只读体检模式（目录或 zip），不进入转换流程
    if args.verify_auto:
        if not args.mod:
            print('[错误] --verify-auto 需要 Mod 路径（zip 或目录）')
            sys.exit(1)
        vpath = os.path.abspath(args.mod)
        if not os.path.exists(vpath):
            print('[错误] 输入不存在:', vpath)
            sys.exit(1)
        tmpdir = None
        if os.path.isdir(vpath):
            vroot = vpath
        else:
            tmpdir = tempfile.mkdtemp(prefix='fwadapt_verify_')
            with zipfile.ZipFile(vpath) as z:
                z.extractall(tmpdir)
            vroot = None
            for r, dirs, files in os.walk(tmpdir):
                if 'modmain.lua' in files:
                    vroot = r
                    break
            vroot = vroot or tmpdir
        print('== 自动文件体检:', vroot)
        try:
            errs, warns = verify_auto_files(vroot, deep=True)
            print('-' * 60)
            print('ERROR %d ｜ WARN %d' % (len(errs), len(warns)))
            if errs:
                print('结论：存在 ERROR，必须修复后再交付（--sync-auto 可重建自动文件）。')
            elif warns:
                print('结论：无 ERROR（WARN 多为可清理的冗余/残留）。')
            else:
                print('结论：全部通过。')
        except Exception as e:
            print('[错误] 体检异常: %s' % e)
            errs = [str(e)]
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        sys.exit(1 if errs else 0)

    # v1.6.4：--audit-aliases 审计模式（不进入转换流程）
    if args.audit_aliases:
        audit_alias_conflicts(args.audit_aliases)
        sys.exit(0)

    # v1.6.0：默认 native 纯原生模式；--legacy-compat 显式切回兼容层（高风险，仅复现用）
    if not args.legacy_compat:
        args.native = True

    # --rebuild-atlas：重建图集静态表后退出（不进入转换流程）
    if args.rebuild_atlas:
        rebuild_atlas_table(args.apk)
        sys.exit(0)

    if not args.mod:
        print('[错误] 缺少 Mod 路径（zip 或目录）')
        sys.exit(1)

    src = os.path.abspath(args.mod)
    if not os.path.exists(src):
        print('[错误] 输入不存在:', src)
        sys.exit(1)

    workdir = None
    cleanup = []
    try:
        # 1) 输入解压/定位
        if os.path.isdir(src):
            workdir = src
        else:
            workdir = tempfile.mkdtemp(prefix='fwadapt_src_')
            cleanup.append(workdir)
            with zipfile.ZipFile(src) as z:
                z.extractall(workdir)
            # 定位含 modmain.lua 的 mod 根目录（zip 可能套了文件夹）
            modroot = None
            for r, dirs, files in os.walk(workdir):
                if 'modmain.lua' in files:
                    modroot = r
                    break
            if modroot is None:
                print('[错误] zip 中未找到 modmain.lua，无法识别 mod 根目录')
                sys.exit(1)
            workdir = modroot

        # 2) modinfo
        #    display_name = modinfo.name 原样（只进 identity_aliases / autotest_suite / 注释）
        #    modname      = 目录身份名（scripts/mods/ 前缀、FW_* 注册名、输出目录、zip 内层目录）
        minfo = os.path.join(workdir, 'modinfo.lua')
        folder = os.path.basename(workdir.rstrip('/\\'))
        display_name = folder
        modid = ''
        if os.path.exists(minfo):
            try:
                t = open(minfo, encoding='utf-8', errors='replace').read()
                display_name, ver, modid = parse_modinfo(t, folder)
            except Exception:
                pass
        if args.id:
            modid = args.id
        modname = mod_fs_name(display_name, folder)
        mk = modkey(display_name)
        if mk == 'mod' and modkey(folder) != 'mod':
            mk = modkey(folder)  # 全中文显示名 → 退回目录名取 ASCII/数字部分，避免所有中文 mod 同 key
        up = mk.upper()
        if display_name != modname:
            print('== Mod 识别: name=%r → 目录身份名=%r id=%r key=%s' % (display_name, modname, modid, mk))
        else:
            print('== Mod 识别: name=%r id=%r key=%s' % (modname, modid, mk))

        # 3) 输出目录
        if args.in_place:
            target = workdir
        else:
            default_out = os.path.join(os.path.dirname(workdir.rstrip('/\\')), modname + '-柠版适配版')
            if os.path.abspath(default_out) == os.path.abspath(workdir):
                target = workdir
            else:
                target = args.out or default_out
                # ★ v1.5.1 安全守卫（严重事故修复）：rmtree 只允许"本工具输出特征名"目录
                #   （*-柠版适配版）。用户显式 --out 已存在且非本工具输出 → 改在其下新建
                #   <modname>-柠版适配版 子目录输出，绝不整目录删除。
                #   事故背景：保存位置误指 Downloads 根 → 全目录被 rmtree 清空（2026-09-15）。
                t_base = os.path.basename(target.rstrip('/\\'))
                if os.path.exists(target) and not t_base.endswith('-柠版适配版'):
                    print('[安全] 输出目标已存在且非本工具输出目录: %s' % target)
                    target = os.path.join(target, modname + '-柠版适配版')
                    print('[安全] 改在其下新建子目录输出: %s' % target)
                if os.path.exists(target):
                    t = os.path.abspath(target).rstrip('/\\').lower()
                    w = os.path.abspath(workdir).rstrip('/\\').lower()
                    tp = os.path.dirname(t)
                    if (t == w or tp == w or os.path.dirname(tp) == w or tp == t
                            or t.endswith(':\\') or t.endswith(':')):
                        print('[错误] 输出目标 %s 与源目录/磁盘根冲突，拒绝删除' % target)
                        sys.exit(1)
                    shutil.rmtree(target)
                shutil.copytree(workdir, target)
            print('== 输出目录:', target)

        # 3.5) 开发者残留清理（v1.6.7）：只删确定用不到的（自动备份包 / FMOD 工程源文件）
        if args.prune_dev:
            removed = prune_dev_assets(target)
            if removed:
                print('== 清理开发者残留: %d 项 / %.2f MB' %
                      (len(removed), sum(sz for _, sz in removed) / 1048576))
                for name, sz in removed[:15]:
                    print('   - %s (%.2f MB)' % (name, sz / 1048576))
                if len(removed) > 15:
                    print('   … 另有 %d 项' % (len(removed) - 15))
            else:
                print('== 清理开发者残留: 未发现可删项')

        # 4) 资源副本（native 模式跳过：手工适配 mod 无 scripts/mods 副本，动画走根 anim/）
        mods_dir = os.path.join(target, 'scripts', 'mods', modname)
        if args.native:
            print('== 资源副本: 跳过（--native 纯原生模式）')
        else:
            if os.path.exists(mods_dir):
                shutil.rmtree(mods_dir)
            os.makedirs(mods_dir, exist_ok=True)
            copied = 0
            for sub in ('anim', 'images', 'minimap', 'sound', 'map'):
                s = os.path.join(target, sub)
                if os.path.isdir(s):
                    shutil.copytree(s, os.path.join(mods_dir, sub), dirs_exist_ok=True)
                    copied += 1
            for f in ('modicon.xml', 'modicon.tex', 'modicon.png'):
                s = os.path.join(target, f)
                if os.path.exists(s):
                    shutil.copy2(s, os.path.join(mods_dir, f))
                    copied += 1
            print('== 资源副本: %d 项 -> scripts/mods/%s/' % (copied, modname))

        # 4.5) 编码统一（v1.6.0 P0）：全量 .lua 统一 UTF-8 BOM + CRLF
        #      （柠版加载器格式敏感；更多料理 559 文件统一后卡加载消失）
        if not args.no_encoding:
            bom_n, crlf_n, skip_n = normalize_encoding(target)
            if bom_n or crlf_n:
                print('== 编码统一: 补 BOM %d 个; 换行归一 %d 个; 跳过(二进制/异常) %d 个' %
                      (bom_n, crlf_n, skip_n))
        else:
            print('== 编码统一: 跳过（--no-encoding）')

        # 5) 纹理转换（并发提速：ThreadPoolExecutor + astcenc 子进程并行，
        #    默认 min(CPU核,6) 并发，--workers 可调；规避 frozen exe multiprocessing 问题）
        if not args.no_tex:
            astcenc = find_astcenc(args.astcenc)
            conv = TexConverter(astcenc=astcenc, prefer_astc=True)
            subs = [os.path.join(target, s)
                    for s in ('anim', 'images', 'minimap', 'sound', 'map')
                    if os.path.isdir(os.path.join(target, s))]
            subs.insert(0, target)  # 根目录独立 tex（scan 自动跳过 scripts/mods）
            st = conv.scan_and_convert(subs, progress=args.progress, workers=args.workers)
            if os.path.isdir(mods_dir):
                st2 = conv.scan_and_convert(mods_dir, workers=args.workers)
                st['converted'] += st2['converted']
                st['failed'] += st2['failed']
                st['astc_already'] += st2['astc_already']
            mode = 'ASTC 8x8' if astcenc else 'RGBA(无 astcenc，回退)'
            print('== 纹理转换(%s): converted=%d failed=%d' % (mode, st['converted'], st['failed']))
            for p, e in conv.failed[:10]:
                print('    FAIL:', p, '->', e)
        else:
            print('== 纹理转换: 跳过（--no-tex）')
        check_cancel()

        if not args.no_autofiles:
            # 6) 自动文件（v1.4.26 + tile_preload_auto.lua：levels/ 自定义地形预加载，§20.25）
            #    v1.6.4：anim_refs = 源码引用动画集合；--keep-dead-anims 可关闭过滤。
            anim_refs = None if args.keep_dead_anims else collect_anim_code_refs(target)
            # ★ v1.6.7：--sync-auto 且未带 --id 时，保留既有 identity_aliases
            keep_ident = []
            if args.sync_auto and not args.id:
                keep_ident = read_identity_aliases(os.path.join(target, 'mod_auto.lua'))
                if keep_ident:
                    print('== identity_aliases 保留: %s' % ', '.join(keep_ident))
            gens = []
            for g, fn in ((gen_mod_auto, 'mod_auto.lua'), (gen_early_prefab, 'early_prefab_auto.lua'),
                          (gen_preload_assets, 'preload_assets_auto.lua'), (gen_sound_banks, 'sound_banks_auto.lua'),
                          (gen_tile_preload, 'tile_preload_auto.lua')):
                try:
                    if g is gen_mod_auto:
                        content = g(target, modname, modid, native=args.native, anim_refs=anim_refs,
                                    display_name=display_name, keep_identity=keep_ident)
                    elif g is gen_early_prefab:
                        content = g(target, modname, native=args.native)
                    elif g is gen_preload_assets:
                        content = g(target, modname, native=args.native)
                    else:
                        content = g(target, modname)
                except Exception as e:
                    print('    [warn] %s 生成失败: %s' % (fn, e))
                    content = None
                if content:
                    p = os.path.join(target, fn)
                    if fn in ('sound_banks_auto.lua', 'tile_preload_auto.lua'):
                        # auto 清单类：无 BOM + CRLF（手工适配 mod 同款）；content 已自带 \r\n，
                        # newline='' 原样写入，避免 newline='\r\n' 把 \n 再转一次成 \r\r\n
                        open(p, 'w', encoding='utf-8', newline='').write(content)
                    else:
                        write_new_lua(p, content)
                    gens.append(fn)
            test_path = os.path.join(target, 'test.lua')
            if args.sync_auto and os.path.exists(test_path):
                # --sync-auto 只刷「资源派生」的自动文件；test.lua 是人工契约，
                # 覆盖掉会把手工补的 surface / blocked 项一起冲掉
                print('== test.lua: 保留现有（--sync-auto 不覆盖已存在的自测契约）')
            else:
                write_new_lua(test_path, gen_test(target, display_name, mk, native=args.native))
                gens.append('test.lua')
            # 收尾：确保 minimap 图集在 preload 清单（v1.6.1 自动补全，斑点灌木实证）
            try:
                ensure_minimap_preload(target, modname)
            except Exception as e:
                print('    [warn] minimap preload 补全失败: %s' % e)
            # ★ v1.6.7：生成后立刻自检（轻量，不深扫 zip）——把「注册表陈旧 / 悬空条目 /
            #   sound_banks schema 不合法」当场报出来，而不是等玩家反馈「动画空白」。
            try:
                _errs, _warns = verify_auto_files(
                    target, modname, deep=False, verbose=False,
                    check_folder=(os.path.basename(target.rstrip('/\\')) == modname))
                for e in _errs:
                    print('    [ERROR] %s' % e)
                for w in _warns:
                    print('    [WARN ] %s' % w)
                if _errs:
                    print('== 自动文件自检: %d ERROR / %d WARN（ERROR 不修就交付 = 大概率动画空白）'
                          % (len(_errs), len(_warns)))
                elif _warns:
                    print('== 自动文件自检: 0 ERROR / %d WARN' % len(_warns))
                else:
                    print('== 自动文件自检: 通过')
            except Exception as e:
                print('    [warn] 自动文件自检异常: %s' % e)
            if args.native:
                print('== 自动文件: %s（--native 不生成 Assets 全量模块：prefab 第三参数由原生引擎收集）' % ', '.join(gens))
            else:
                # ★ 全量 Assets 声明模块（柠版 build 注册通道）：prefab 内 Asset 提升到 modmain 级
                assets_mod = gen_assets_auto(target, modname, mk)
                if assets_mod:
                    gens.append(os.path.relpath(assets_mod, target).replace('\\', '/'))
                print('== 自动文件: %s' % ', '.join(gens))
        check_cancel()

        # 7) native 模式：动画加载走 early_prefab_auto.lua 全量 build 注册
        #    （gen_early_prefab native 分支已生成 298 条全 zip 条目，§20.14 实证唯一有效通道）。
        #    Assets 表补缺 / FW_PreloadAssets 两通道已实证无效（柠版不读 Assets 表 ANIM、
        #    FW_PreloadAssets 无副本路径不生效）——仅 --with-legacy-injects 显式保留（复现用）。
        if args.native:
            if args.with_legacy_injects:
                assets = collect_all_assets(target)
                assets = collect_anim_zips(target, assets)
                assets = filter_needed_anims(target, assets)
                n_anim = inject_assets_append(target, assets)
                print('== [废弃通道] Assets 追加: %d 条 ANIM（实证无效，勿用于生产）' % n_anim)
                n_fw = inject_fw_preload(target, modname)
                print('== [废弃通道] FW_PreloadAssets 注入: %d（实证未生效）' % n_fw)
            else:
                print('== 动画通道: early_prefab_auto.lua 全量 build 注册（§20.14 唯一有效通道）')
        elif not args.no_compat:
            replicas = collect_replicas(target)
            # 全量动画清单：资源副本 anim/ 下的全部 zip（生成期收集，兼容层硬编码）
            mods_anim_dir = os.path.join(target, 'scripts', 'mods', modname, 'anim')
            anim_list = ['anim/%s' % f for f in sorted(os.listdir(mods_anim_dir))
                         if f.endswith('.zip')] if os.path.isdir(mods_anim_dir) else []
            compat_lua = os.path.join(target, 'scripts', 'mobile_compat_%s.lua' % mk)
            os.makedirs(os.path.dirname(compat_lua), exist_ok=True)
            write_new_lua(compat_lua, render_compat(modname, mk, replicas, not args.no_recipes, anim_list))
            print('== 兼容层: scripts/mobile_compat_%s.lua（Replica: %s; 全量动画兜底预加载: %d 个）' % (mk, ', '.join(replicas) or '无', len(anim_list)))
            for msg in inject_modmain(target, modname, mk):
                print('   -', msg)
        else:
            print('== 兼容层: 跳过（--no-compat）')
        check_cancel()

        if not args.no_rules:
            # 7.5) 通用规则注入（不依赖 per-mod 补丁，全部自动）：
            #      a) ModManager.RegisterPrefabs hook → AddSimPostInit 延迟执行（金锅类配方）
            #      b) PC 固定坐标面板/按钮 → FW_RegisterModButton 柠版按钮注册
            n_hook = convert_registerprefabs_hook(target)
            if n_hook:
                print('== 通用规则: RegisterPrefabs hook → AddSimPostInit 转换 %d 个文件' % n_hook)
            char_btn = find_character(target)
            n_btn = inject_mod_buttons(target, modname, character=char_btn)
            if n_btn:
                print('== 通用规则: 柠版按钮自动注册 %d 个（FW_RegisterModButton%s）' %
                      (n_btn, '，character=' + char_btn if char_btn else ''))
        check_cancel()

        if not args.no_key_buttons:
            # 7.6) 角色按键技能 → 柠版按钮（独立可选项，与 --no-rules 分离）
            char_key = find_character(target)
            n_key = inject_key_buttons(target, modname, use_simulate=args.simulate_key, character=char_key)
            if n_key:
                print('== 角色技能按钮: 按键技能 → FW_RegisterAction+柠版按钮 %d 个（%s）' %
                      (n_key, 'FW_SimulateKey 模拟键' if args.simulate_key else 'reuse_action 成对'))
            # 7.7) 角色 mod 自动生成 FW_RegisterCharacter 调用（角色入列三件套之一）
            if inject_register_character(target, modname):
                print('== 角色框架: FW_RegisterCharacter 自动生成注入（角色: %s）' % (char_key or '扫描'))
        check_cancel()

        # 8) 兼容性 post-fix：PC 老代码 Lua 5.1 隐式 arg 表在柠版(新 Lua)为 nil
        #    a) `_G.unpack(arg)` → `_G.unpack({...})`（Lua 5.1 语义等价，5.2+ 修崩溃）
        #    b) vararg 函数内裸用隐式 arg（aipCountTable(arg)/entMatchNames(arg,ent)）
        #       → 注入 `local arg={...}`（AIP 实测：aipCommonStr/aipFindEnt/aipFindEnts/
        #       aipCountEnts/aipIndexEnts 进入世界后 pairs(nil) 闪退）
        if not args.no_postfix:
            fix_arg_count = 0
            fix_argvar_count = 0
            func_re = re.compile(r'^\s*function\s+[\w.:]+\s*\([^)]*\.\.\.[^)]*\)\s*(?:--.*)?$')
            for r, dirs, files in os.walk(target):
                for f in files:
                    if not f.endswith('.lua'):
                        continue
                    p = os.path.join(r, f)
                    try:
                        raw = open(p, 'rb').read()
                    except Exception:
                        continue
                    if b'unpack(arg)' not in raw and not re.search(rb'\barg\b', raw):
                        continue
                    bom = raw.startswith(b'\xef\xbb\xbf')
                    text = raw.decode('utf-8-sig', errors='replace')
                    # a) unpack(arg)
                    n = text.count('_G.unpack(arg)') + text.count('unpack(arg)')
                    if n:
                        text = text.replace('_G.unpack(arg)', '_G.unpack({...})').replace('unpack(arg)', 'unpack({...})')
                    # b) vararg 函数裸用 arg → 注入 local arg={...}
                    lines = text.split('\n')
                    t_idx = [i for i, l in enumerate(lines) if func_re.match(l)]
                    for idx in sorted(t_idx, reverse=True):
                        end = len(lines)
                        for j in range(idx + 1, len(lines)):
                            if re.match(r'^\s*function\s', lines[j]):
                                end = j
                                break
                        body = '\n'.join(lines[idx:end])
                        if re.search(r'local\s+arg\s*=', body):      # 已有显式 local arg
                            continue
                        if re.search(r'\barg\b', lines[idx]):        # 参数名就叫 arg
                            continue
                        if not re.search(r'\barg\b', body):
                            continue
                        j = idx + 1
                        while j < end and (lines[j].strip() == '' or lines[j].strip().startswith('--')):
                            j += 1
                        if j >= end:
                            continue
                        ind = re.match(r'\s*', lines[j]).group(0)
                        lines.insert(j, ind + 'local arg={...}')
                        fix_argvar_count += 1
                    text = '\n'.join(lines)
                    if n or fix_argvar_count:
                        out = text.encode('utf-8')
                        if bom:
                            out = b'\xef\xbb\xbf' + out
                        open(p, 'wb').write(out)
                        fix_arg_count += n
            if fix_arg_count:
                print('== 兼容性 post-fix: unpack(arg)->unpack({...}) 共 %d 处' % fix_arg_count)
            if fix_argvar_count:
                print('== 兼容性 post-fix: vararg 注入 local arg={...} 共 %d 处' % fix_argvar_count)
        check_cancel()

        # 8.4) 通用防御性修复注入（fx/target 判空 + 滚动条 lastx/lasty 兜底）
        #      ——英雄联盟武器手工版 10 个 prefab nil 防护 + scrollablelist 触屏
        #      lastx 崩溃的通用化，对任意 Mod 自动生效；已修复文件幂等跳过。
        if not args.no_defensive:
            fx_n, tg_n, lx_n, sd_n, it_n, sp_n = inject_defensive_fixes(target)
            if fx_n or tg_n or lx_n or sd_n or it_n or sp_n:
                print('== 防御性修复: fx 判空 %d 处; target 判空 %d 处; lastx/lasty 兜底 %d 处; SetOnDown 记录 %d 处; items越界SetFocus判空 %d 处; SpawnPrefab链式判空 %d 处' %
                      (fx_n, tg_n, lx_n, sd_n, it_n, sp_n))
        check_cancel()

        # 8.405) worldgen 链 _G 别名（v1.6.0 P0）：modworldgenmain 隔离 env 无裸 Lua 内置
        n_wg = inject_worldgen_globals(target)
        if n_wg:
            print('== worldgen 链: 注入 _G 别名 %d 个文件（pcall/type/pairs/ipairs/tostring）' % n_wg)

        # 8.406) 原版图集修正（v1.6.0 P0）：读静态表，改 recipe.atlas 指柠版原版图集
        if not args.no_atlas_fix:
            table = load_vanilla_atlas(args.atlas or args.apk)
            if table:
                r2a = table.get('region_to_atlas') or {}
                imgs = scan_vanilla_atlas_recipes(target)
                fix_map = {}
                for img in imgs:
                    atl = r2a.get(img)
                    if atl:
                        fix_map[img] = atl
                if fix_map:
                    n = inject_vanilla_atlas_fix(target, modname, fix_map, mk=mk)
                    print('== 原版图集修正: 读静态表，命中 %d 个 recipe（→ 柠版原版图集）' % n)
                else:
                    print('== 原版图集修正: 扫描 %d 个 recipe image，表无命中' % len(imgs))
            else:
                print('== 原版图集修正: 未找到静态表（vanilla_atlas_*.json），跳过'
                      '（用 --rebuild-atlas --apk <APK> 生成）')
        else:
            print('== 原版图集修正: 跳过（--no-atlas-fix）')

        # 8.41) 生命周期任务重写（v1.5.0）：DoTaskInTime/DoPeriodicTask 成对 Cancel
        #       → __FW_LIFE_*（FW_DoTaskInTime/FW_DoPeriodicTask/FW_CancelLifecycle 托管，
        #       pcall 回退原生，不改变一次性任务语义）
        if not args.no_lifecycle:
            n_life = inject_lifecycle_tasks(target, modname)
            if n_life:
                print('== 生命周期任务: 重写 %d 个文件（FW_* 生命周期托管 + 原生回退）' % n_life)
        check_cancel()

        # 8.42) 触摸管线兼容（v1.5.0）：OnTouchLong/OnGesture 补全 + 防误触/屏幕拾取 helper
        if not args.no_touch_pipeline:
            if inject_touch_pipeline(target, modname):
                print('== 触摸管线: OnTouchLong/OnGesture 补全 + __FW_TOUCH_GUARD/__FW_TOUCH_ENTITIES 注入')

        # 8.43) 预制物全局垫片 + 图标图集反查（v1.6.1，实机日志实施）
        #   ① 框架在 idle 阶段批量 restore mod 预制物，早于原版 prefablist → 由原版预制物文件
        #      「顺带定义」的 GetAllWinterOrnamentPrefabs / ASSETS 还不存在，mod 文件首行即报错，
        #      整文件作废（虚空异界实测丢 8 个预制物：宝藏袋 5 + 黑匣 2 + 打蜡植物 1）。
        #   ② 柠版 inventoryitem:GetAtlas() 对 mod 物品回落 images/inventoryimages4.xml，
        #      面板 SetTexture 找不到 region → 图标空白。改用 AtlasContains 反查。
        #   两步共用同一块 modmain 垫片（幂等 __FW_PREFAB_GLOBAL_SHIM），图集清单每次重生成。
        n_atlas = gen_atlas_index(target, modname)
        if n_atlas:
            print('== 图集索引: scripts/tr_atlas_index_auto.lua（%d 条，供图标反查）' % n_atlas)
        if inject_prefab_global_shim(target, modname):
            print('== 预制物全局垫片: GetAllWinterOrnamentPrefabs/ASSETS + __TR_FIND_ATLAS 注入 modmain')

        if not args.no_scroll:
            # 8.5) 柠版触摸滚动适配（可选 --touch-scroll）：滑块/滑动区域
            # ★ 直接改滚动类文件（inject_touch_scroll_files，不碰 modmain）：
            #   AIP §20.15.2 实证 modmain require 注入路线在柠版卡加载（require 时机/路径风险），
            #   文件内注入 = 手工书籍触摸版同构（类方法 + ctor 包装，实例化才生效）。
            if args.touch_scroll:
                n_scroll = inject_touch_scroll_files(target)
                if n_scroll:
                    print('== 触摸滚动适配: 注入 %d 个滚动类（--touch-scroll，改文件注入）' % n_scroll)
                else:
                    print('== 触摸滚动适配: 未发现自定义滚动类（--touch-scroll，跳过）')

            # 8.6) ScrollableList 系拖动重写（自动，无需开关）：标准 ScrollableList 在柠版
            #      触摸下原版 DoDragScroll 坐标换算错乱 → 拖动无效（LOL 图鉴左侧实证）。
            #      注入手工版同构：SetOnDown 立即 LockFocus+dragging + DoDragScroll 重写
            #      （手指 y→滑轨比例→ScrollToRatio）+ OnUpdate 每帧平滑逼近。
            #      与 --touch-scroll 的跳过条件互斥（同判 DoDragScroll+position_marker）。
            n_drag = inject_scrollablelist_drag(target)
            if n_drag:
                print('== 滚动条拖动重写: %d 个 ScrollableList 系（手指y→滑轨比例→ScrollToRatio 平滑）' % n_drag)
        check_cancel()

        # 8.9) 收尾编码统一（v1.6.0）：后续注入步骤可能改写文件，最后再统一一次 BOM+CRLF
        #      （注入函数写回可能 LF；收尾统一 = 最终防线，幂等）
        if not args.no_encoding:
            bom_n2, crlf_n2, skip_n2 = normalize_encoding(target)
            if bom_n2 or crlf_n2:
                print('== 收尾编码统一: 补 BOM %d 个; 换行归一 %d 个' % (bom_n2, crlf_n2))

        # 9) 打包
        if args.zip:
            outzip = os.path.join(os.path.dirname(target.rstrip('/\\')), modname + '-柠版适配版.zip')
            if os.path.exists(outzip):
                os.remove(outzip)
            with zipfile.ZipFile(outzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                n = 0
                for r, dirs, files in os.walk(target):
                    for f in files:
                        p = os.path.join(r, f)
                        # 条目必须正斜杠（Windows 的 os.path.join 会给反斜杠 → 柠版解压后层级错乱）
                        arc = (modname + '/' + os.path.relpath(p, target).replace('\\', '/'))
                        z.write(p, arc)
                        n += 1
            print('== 打包: %s (%d 文件, %.1f MB)' % (outzip, n, os.path.getsize(outzip)/1024/1024))

        print('== 完成。目标目录: %s' % target)
        # ★ 安装命名铁律（v1.6.6）：mods 目录下的文件夹名必须 == modname。
        #   框架 resources/asset_resolver.lua:165-168 校验
        #   asset_case_aliases 的每个值必须以 scripts/mods/<已安装文件夹名>/ 开头，
        #   否则报 invalid asset alias owner（值里写死的 owner 不会跟着改名走）。
        print('== 安装：放进柠版 mods 目录时，文件夹名必须是 "%s"' % modname)
        print('   （scripts/mods/%s/ 前缀已写死在自动文件里，带 -柠版适配版 后缀装进去会报 invalid asset alias owner）' % modname)
    finally:
        for d in cleanup:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    main()
