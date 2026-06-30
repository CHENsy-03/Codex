"""实时流查看器（show_stream 别名）

文档3.docx line62要求此文件名。
实际功能委托给 cli/stream_view.py。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
print("提示: show_stream.py 已整合到 cli/stream_view.py")
print("请使用: python -m cli.stream_view --topic gps.data\n")
from cli.stream_view import main
if __name__ == "__main__":
    main()
