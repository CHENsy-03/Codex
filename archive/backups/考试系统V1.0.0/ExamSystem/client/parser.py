#!/usr/bin/env python3
"""
独立解析器 —— 将 Word .docx 题库转换为 questions.json。

用法：
    python parser.py <input.docx> [output.json]

    若省略 output.json，默认输出为当前目录下的 questions.json。
"""

import sys
import json
import os
# Ensure python-docx is bundled by PyInstaller (lazy import in question_parser)
try:
    import docx
except ImportError:
    pass


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "questions.json"

    if not os.path.exists(input_path):
        print(f"错误：文件不存在 - {input_path}")
        sys.exit(1)

    try:
        from parser.docx_parser import parse_docx

        print(f"解析 {os.path.basename(input_path)}...", end=" ", flush=True)
        questions = parse_docx(input_path)

        if not questions:
            print()
            print("错误：未解析到有效题目")
            sys.exit(1)

        from export.json_export import export_to_json
        export_to_json(questions, output_path)

        print("完成。")
        print(f"已导出 {len(questions)} 道题到 {output_path}")

    except ImportError as e:
        print()
        print(f"错误：缺少依赖 - {e}")
        print("请运行: pip install python-docx")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()