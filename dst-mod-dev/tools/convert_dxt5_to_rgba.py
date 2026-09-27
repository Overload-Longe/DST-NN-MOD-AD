# -*- coding: utf-8 -*-
"""
柠版（手机端 DST）贴图黑块修复工具
====================================
将 Mod 目录下 anim/*.zip 内所有 DXT5/BC3 纹理转换为无压缩 RGBA KTEX。
修复 Android Mali GPU 不支持 DXT/BC 压缩导致的"纯黑块"问题。

KTEX 格式（逆向确认）:
  Header: 8 字节 ("KTEX" + uint32 LE header)
    compression   = bit 4-8   (2=DXT5, 4=RGBA)
    mipmap_count  = bit 13-17
    flags         = bit 18+   (0=RGBA, 3=DXT5)
  每 mip: 10 字节 pre (uint16 w, uint16 h, uint16 pitch, uint32 datasz)
  随后按序排列 mip 像素数据。

用法:
  python convert_dxt5_to_rgba.py <Mod根目录>
  # 示例: python convert_dxt5_to_rgba.py "D:\\mods\\趣味食物"

注意:
  - 只改 anim/*.zip 内的 *.tex, build.bin / anim.bin 保持不变
  - 独立 .tex(物品栏图集/modicon/图鉴/minimap) 通常已是 RGBA, 跳过
"""
import zipfile, glob, os, struct, sys, time

MOD_ROOT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()


def rgb565(c):
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return (r, g, b)


def decompress_dxt5_block(block):
    """解压一个 16 字节 DXT5 块 -> 16 个 RGBA 像素 (64 字节)."""
    alpha0 = block[0]
    alpha1 = block[1]
    ai = block[2] | (block[3] << 8) | (block[4] << 16) | (block[5] << 24) | (block[6] << 32) | (block[7] << 40)
    c0 = block[8] | (block[9] << 8)
    c1 = block[10] | (block[11] << 8)
    ci = block[12] | (block[13] << 8) | (block[14] << 16) | (block[15] << 24)

    if alpha0 > alpha1:
        a2 = ((6 * alpha0 + 1 * alpha1) // 7)
        a3 = ((5 * alpha0 + 2 * alpha1) // 7)
        a4 = ((4 * alpha0 + 3 * alpha1) // 7)
        a5 = ((3 * alpha0 + 4 * alpha1) // 7)
        a6 = ((2 * alpha0 + 5 * alpha1) // 7)
        a7 = ((1 * alpha0 + 6 * alpha1) // 7)
        alpha = (alpha0, alpha1, a2, a3, a4, a5, a6, a7)
    else:
        a2 = ((4 * alpha0 + 1 * alpha1) // 5)
        a3 = ((3 * alpha0 + 2 * alpha1) // 5)
        a4 = ((2 * alpha0 + 3 * alpha1) // 5)
        a5 = ((1 * alpha0 + 4 * alpha1) // 5)
        alpha = (alpha0, alpha1, a2, a3, a4, a5, 0, 255)

    r0, g0, b0 = rgb565(c0)
    r1, g1, b1 = rgb565(c1)
    if c0 > c1:
        r2 = (2 * r0 + r1) // 3; g2 = (2 * g0 + g1) // 3; b2 = (2 * b0 + b1) // 3
        r3 = (r0 + 2 * r1) // 3; g3 = (g0 + 2 * g1) // 3; b3 = (b0 + 2 * b1) // 3
    else:
        r2 = (r0 + r1) // 2; g2 = (g0 + g1) // 2; b2 = (b0 + b1) // 2
        r3 = 0; g3 = 0; b3 = 0

    out = bytearray(64)
    for p in range(16):
        a = alpha[(ai >> (p * 3)) & 7]
        cidx = (ci >> (p * 2)) & 3
        o = p * 4
        if cidx == 0:
            out[o] = r0; out[o + 1] = g0; out[o + 2] = b0
        elif cidx == 1:
            out[o] = r1; out[o + 1] = g1; out[o + 2] = b1
        elif cidx == 2:
            out[o] = r2; out[o + 1] = g2; out[o + 2] = b2
        else:
            out[o] = r3; out[o + 1] = g3; out[o + 2] = b3
        out[o + 3] = a
    return out


def decompress_dxt5(data, width, height):
    """DXT5 数据 -> RGBA 字节."""
    result = bytearray(width * height * 4)
    bw = (width + 3) // 4
    bh = (height + 3) // 4
    for by in range(bh):
        y0 = by * 4
        for bx in range(bw):
            x0 = bx * 4
            block_off = (by * bw + bx) * 16
            block = data[block_off:block_off + 16]
            pixels = decompress_dxt5_block(block)
            for py in range(4):
                y = y0 + py
                if y >= height:
                    break
                dst_off = (y * width + x0) * 4
                src_off = py * 16
                copy_w = min(4, width - x0)
                result[dst_off:dst_off + copy_w * 4] = pixels[src_off:src_off + copy_w * 4]
    return bytes(result)


def convert_tex(data):
    """转换一个 KTEX 文件 DXT5 -> RGBA. 返回 (新字节, 说明) 或 (None, 原因)."""
    if data[0:4] != b'KTEX':
        return None, "not KTEX"
    hdr_val = struct.unpack('<I', data[4:8])[0]
    compression = (hdr_val >> 4) & 0x1F
    mipmap_count = (hdr_val >> 13) & 0x1F

    if compression == 4:
        return data, "already RGBA"
    if compression != 2:
        return None, "unsupported compression %d" % compression

    mips = []
    offset = 8
    for i in range(mipmap_count):
        w = struct.unpack('<H', data[offset:offset + 2])[0]
        h = struct.unpack('<H', data[offset + 2:offset + 4])[0]
        pitch = struct.unpack('<H', data[offset + 4:offset + 6])[0]
        datasz = struct.unpack('<I', data[offset + 6:offset + 10])[0]
        mips.append((w, h, pitch, datasz))
        offset += 10

    data_start = offset
    rgba_mips = []
    cur = data_start
    for w, h, pitch, datasz in mips:
        dxt_data = data[cur:cur + datasz]
        rgba = decompress_dxt5(dxt_data, w, h)
        rgba_mips.append((w, h, rgba))
        cur += datasz

    # 新 header: compression=4 (RGBA), flags=0
    new_hdr = hdr_val & ~(0x1F << 4) & ~(3 << 18) | (4 << 4)
    out = bytearray()
    out += b'KTEX'
    out += struct.pack('<I', new_hdr)
    for w, h, rgba in rgba_mips:
        pitch = w * 4
        datasz = w * h * 4
        out += struct.pack('<HHH', w, h, pitch)
        out += struct.pack('<I', datasz)
    for w, h, rgba in rgba_mips:
        out += rgba

    return bytes(out), "converted DXT5->RGBA (%d -> %d bytes)" % (len(data), len(out))


def main():
    if not os.path.isdir(os.path.join(MOD_ROOT, 'anim')):
        print('未找到 anim 目录:', MOD_ROOT)
        sys.exit(1)
    os.chdir(MOD_ROOT)
    zips = sorted(glob.glob('anim/*.zip'))
    total_converted = 0
    total_skipped = 0
    t0 = time.time()

    for zi, zf in enumerate(zips):
        z = zipfile.ZipFile(zf, 'r')
        names = z.namelist()
        has_tex = any(n.endswith('.tex') for n in names)
        if not has_tex:
            z.close()
            continue
        entries = {}
        for n in names:
            entries[n] = z.read(n)
        z.close()

        changed = False
        for n in list(entries.keys()):
            if n.endswith('.tex'):
                new_data, msg = convert_tex(entries[n])
                if new_data is not None and new_data != entries[n]:
                    entries[n] = new_data
                    changed = True
                    total_converted += 1
                    print('  [%d/%d] %s/%s: %s' % (zi + 1, len(zips), zf, n, msg))
                elif new_data == entries[n]:
                    total_skipped += 1

        if changed:
            tmp = zf + '.tmp'
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
                for n, d in entries.items():
                    zout.writestr(n, d)
            os.replace(tmp, zf)
            print('  -> rewrote %s' % zf)

    elapsed = time.time() - t0
    print('\nDone: %d tex converted, %d skipped, %.1fs' % (total_converted, total_skipped, elapsed))


if __name__ == '__main__':
    main()
