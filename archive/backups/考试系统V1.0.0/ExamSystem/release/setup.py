"""考试系统 安装程序"""
import os, sys, shutil, subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

def resource_path():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def copy_tree(src, dst):
    skip_ext = (".py", ".pyc", ".pyo", ".spec")
    for item in os.listdir(src):
        if any(item.endswith(e) for e in skip_ext):
            continue
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)

def create_shortcut(target, link, work_dir):
    ps = '$ws = New-Object -ComObject WScript.Shell;'
    ps += '$s = $ws.CreateShortcut("%s.lnk");' % link
    ps += '$s.TargetPath = "%s";' % target
    ps += '$s.WorkingDirectory = "%s";' % work_dir
    ps += '$s.Description = "离线考试系统";'
    ps += '$s.Save()'
    subprocess.run(["powershell","-NoProfile","-Command",ps],
                   capture_output=True, timeout=30)

def main():
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno("安装考试系统",
            "即将安装离线考试系统到您的电脑。\n\n是否继续？"):
        return
    default = os.path.join(os.environ.get("ProgramFiles","C:\\Program Files"),
                           "ExamSystem")
    install = filedialog.askdirectory(title="选择安装目录",
                                      initialdir=default)
    if not install:
        return
    if not install.rstrip("\\").endswith("ExamSystem"):
        install = os.path.join(install, "ExamSystem")
    try:
        src = resource_path()
        os.makedirs(install, exist_ok=True)
        copy_tree(src, install)
        for sub in ("logs","data\\sessions","data\\backup"):
            os.makedirs(os.path.join(install, sub), exist_ok=True)
        try:
            desktop = os.path.join(os.environ["USERPROFILE"],"Desktop",
                                   "考试系统")
            create_shortcut(os.path.join(install,"考试系统.exe"),
                            desktop, install)
        except Exception:
            pass
        done = "考试系统已安装到：\n%s\n\n桌面快捷方式已创建。" % install
        messagebox.showinfo("安装完成", done)
    except Exception as e:
        messagebox.showerror("安装失败",
                             "安装过程出现错误：\n%s" % e)

if __name__ == "__main__":
    main()
