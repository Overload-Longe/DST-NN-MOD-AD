# -*- coding: utf-8 -*-
"""柠版 Mod 一键适配工具 GUI（v1.5.2）。

- 进程内调用 dst_mobile_adapter（不弹 cmd，后台运行）
- 进度条：解析纹理转换阶段 PROGRESS:n/total
- 取消：置 ADA._CANCEL = True（adapter v1.4.22+ 阶段检查点中断）
- Mod 文件与保存位置：两个选择器独立记忆上次路径
- 所有流程可勾选（native 默认）
- v1.5.2：防御规则新增 SpawnPrefab 链式调用判空（行首 SpawnPrefab(x).Method 拆两行判空，
  Forge 专属 prefab 缺失→nil 崩溃通用修复；心之钢实证）
- v1.5.1：输出目录 rmtree 安全守卫（adapter 侧：非"*-柠版适配版"目录不删除，改子目录输出）
"""
import os
import sys
import json
import queue
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE_DIR, 'tool_gui_config.json')

import dst_mobile_adapter as ADA  # noqa: E402


class TextRedirector:
    """线程安全 stdout/stderr 重定向：写入 queue，主线程 poll 刷新。"""
    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(s)

    def flush(self):
        pass


class AdapterApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.worker = None
        self.running = False
        self.cfg = self.load_config()

        root.title('柠版 Mod 一键适配工具')
        root.resizable(False, False)  # 取消边缘拉拽缩放
        self.build_ui()
        self.root.after(100, self.poll_queue)

    # ---------- 配置记忆（Mod 文件 / 保存位置 分开） ----------
    def load_config(self):
        try:
            with open(CONFIG, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self):
        try:
            with open(CONFIG, 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- UI ----------
    def build_ui(self):
        pad = {'padx': 8, 'pady': 3}

        # 第 1 行：Mod 文件
        f1 = ttk.Frame(self.root)
        f1.pack(fill='x', **pad)
        ttk.Label(f1, text='Mod 文件:').pack(side='left')
        self.var_mod = tk.StringVar(value=self.cfg.get('mod', ''))
        e = ttk.Entry(f1, textvariable=self.var_mod)
        e.pack(side='left', fill='x', expand=True, padx=4)
        ttk.Button(f1, text='选择zip', width=8, command=self.pick_zip).pack(side='left', padx=2)
        ttk.Button(f1, text='选择文件夹', width=9, command=self.pick_dir).pack(side='left', padx=2)

        # 第 2 行：保存位置
        f2 = ttk.Frame(self.root)
        f2.pack(fill='x', **pad)
        ttk.Label(f2, text='保存位置:').pack(side='left')
        self.var_out = tk.StringVar(value=self.cfg.get('out', ''))
        e2 = ttk.Entry(f2, textvariable=self.var_out)
        e2.pack(side='left', fill='x', expand=True, padx=4)
        ttk.Button(f2, text='选择文件夹', width=9, command=self.pick_out).pack(side='left', padx=2)

        # 第 3 行：流程选项（勾选）
        f3 = ttk.LabelFrame(self.root, text='处理流程（全部可选）')
        f3.pack(fill='x', **pad)
        self.opts = {}
        opts_spec = [
            ('native', 'native 纯原生模式（默认）', True),
            ('tex',   '纹理转换（ASTC 8x8）', True),
            ('compat', '兼容层注入（FW_* / Replica）', True),
            ('rules', '通用规则（按钮注册+配方hook）', True),
            ('keybtn', '角色按键技能→柠版按钮(FW_Action)', True),
            ('lifecycle', '生命周期任务重写（FW_托管）', True),
            ('touchpl', '触摸管线兼容（OnTouchLong/手势）', True),
            ('scroll', '滑动/滑块适配', True),
            ('postfix', 'Lua5.1 兼容 post-fix', True),
            ('defensive', '防御性修复（判空/兜底）', True),
            ('autofiles', '自动文件生成（含tile_preload）', True),
            ('zip', '打包 zip', True),
        ]
        for i, (k, label, default) in enumerate(opts_spec):
            v = tk.BooleanVar(value=self.cfg.get('opt_' + k, default))
            self.opts[k] = v
            ttk.Checkbutton(f3, text=label, variable=v).grid(row=i // 2, column=i % 2, sticky='w', padx=6, pady=1)

        # 第 4 行：并发 + 操作
        f4 = ttk.Frame(self.root)
        f4.pack(fill='x', **pad)
        ttk.Label(f4, text='并发数:').pack(side='left')
        _wk = self.cfg.get('workers')
        if _wk in (None, '', 0, '0'):
            _wk = '自动'
        self.var_workers = tk.StringVar(value=str(_wk))
        cb = ttk.Combobox(f4, textvariable=self.var_workers, values=['自动'] + [str(i) for i in range(1, 9)], width=5, state='readonly')
        cb.pack(side='left', padx=4)
        ttk.Button(f4, text='开始转换', command=self.start).pack(side='left', padx=6)
        ttk.Button(f4, text='取消', command=self.cancel).pack(side='left', padx=2)
        ttk.Button(f4, text='打开输出文件夹', command=self.open_out).pack(side='right', padx=2)

        # 进度条
        self.prog = ttk.Progressbar(self.root, mode='determinate', maximum=100)
        self.prog.pack(fill='x', **pad)

        # 日志
        self.log = tk.Text(self.root, height=16, state='disabled', font=('Consolas', 9))
        self.log.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.log.tag_configure('err', foreground='red')

    # ---------- 选择器 ----------
    def pick_zip(self):
        init = self.cfg.get('mod', '')
        init = init if os.path.isdir(init) else os.path.dirname(init)
        p = filedialog.askopenfilename(initialdir=init or None, title='选择 Mod 的 zip 压缩包',
                                       filetypes=[('zip', '*.zip'), ('所有文件', '*.*')])
        if p:
            self.var_mod.set(p)
            self.cfg['mod'] = p
            self.save_config()

    def pick_dir(self):
        init = self.cfg.get('mod', '')
        init = init if os.path.isdir(init) else os.path.dirname(init)
        p = filedialog.askdirectory(initialdir=init or None, title='选择 Mod 文件夹')
        if p:
            self.var_mod.set(p)
            self.cfg['mod'] = p
            self.save_config()

    def pick_out(self):
        init = self.cfg.get('out', '') or os.path.dirname(self.cfg.get('mod', ''))
        p = filedialog.askdirectory(initialdir=init or None, title='选择保存位置（输出目录）')
        if p:
            self.var_out.set(p)
            self.cfg['out'] = p
            self.save_config()

    def open_out(self):
        out = self.var_out.get().strip()
        if out and os.path.isdir(out):
            os.startfile(out)
        else:
            messagebox.showinfo('提示', '请先选择有效的保存位置')

    # ---------- 执行 ----------
    def build_args(self, src, out):
        """构造 adapter CLI 参数列表（对应 --no-* 语义）。"""
        argv = ['dst_mobile_adapter.py', src, '--out', out, '--progress']
        o = self.opts
        # native 模式：资源副本/兼容层/FW_ 注入由 adapter 内部跳过，无需传 no-compat/no-rules
        if o['native'].get():
            argv.append('--native')
        if not o['tex'].get():
            argv.append('--no-tex')
        if not o['compat'].get():
            argv.append('--no-compat')
        if not o['rules'].get():
            argv.append('--no-rules')
        if not o['keybtn'].get():
            argv.append('--no-key-buttons')
        if not o['lifecycle'].get():
            argv.append('--no-lifecycle')
        if not o['touchpl'].get():
            argv.append('--no-touch-pipeline')
        if not o['scroll'].get():
            argv.append('--no-scroll')
        else:
            argv.append('--touch-scroll')
        if not o['postfix'].get():
            argv.append('--no-postfix')
        if not o['defensive'].get():
            argv.append('--no-defensive')
        if not o['autofiles'].get():
            argv.append('--no-autofiles')
        if o['zip'].get():
            argv.append('--zip')
        w = self.var_workers.get().strip()
        if w.isdigit():
            argv.append('--workers')
            argv.append(w)
        return argv

    def start(self):
        if self.running:
            return
        src = self.var_mod.get().strip()
        out = self.var_out.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showwarning('提示', '请先选择有效的 Mod 文件或文件夹')
            return
        if not out:
            out = os.path.dirname(src.rstrip('/\\'))
            self.var_out.set(out)
        # 记录配置
        self.cfg['mod'] = src
        self.cfg['out'] = out
        for k, v in self.opts.items():
            self.cfg['opt_' + k] = v.get()
        wkv = self.var_workers.get().strip()
        self.cfg['workers'] = '自动' if wkv in ('', '0') else wkv
        self.save_config()

        self.clear_log()
        self.prog['value'] = 0
        self.running = True
        ADA._CANCEL = False
        argv = self.build_args(src, out)
        self.log_line('>> ' + ' '.join(argv) + '\n')

        self.worker = threading.Thread(target=self.run_adapter, args=(argv,), daemon=True)
        self.worker.start()

    def run_adapter(self, argv):
        """线程内调用 adapter.main()：临时替换 sys.argv / stdout，捕获 SystemExit。"""
        old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
        sys.argv = argv
        sys.stdout = TextRedirector(self.q)
        sys.stderr = TextRedirector(self.q)
        try:
            ADA.main()
            self.q.put('\n[完成] 适配完成\n')
        except SystemExit as e:
            if e.code == 130:
                self.q.put('\n[已取消]\n')
            else:
                self.q.put('\n[退出码 %s]\n' % e.code)
        except Exception as e:
            self.q.put('\n[错误] %s\n%s\n' % (e, traceback.format_exc()))
        finally:
            sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
            self.q.put('__DONE__')

    def cancel(self):
        if self.running:
            ADA._CANCEL = True
            self.log_line('[提示] 取消请求已发送，将在当前阶段检查点中断\n')

    # ---------- 日志/进度 ----------
    def log_line(self, s, tag=None):
        self.log.config(state='normal')
        self.log.insert('end', s, tag or ())
        self.log.see('end')
        self.log.config(state='disabled')

    def clear_log(self):
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.config(state='disabled')

    def poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item == '__DONE__':
                    self.running = False
                    self.prog['value'] = 100
                    continue
                if item.startswith('PROGRESS:'):
                    try:
                        d, t = item[len('PROGRESS:'):].strip().split('/')
                        d, t = int(d), int(t)
                        if t > 0:
                            self.prog['value'] = min(100, int(d * 100 / t))
                    except Exception:
                        pass
                    continue
                self.log_line(item)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)


def main():
    root = tk.Tk()
    root.geometry('560x580')
    AdapterApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
