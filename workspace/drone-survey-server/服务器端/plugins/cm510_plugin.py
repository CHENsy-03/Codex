"""CM510 协议解析插件（cm510_plugin 别名）

文档3.docx line274要求此文件名。
实际解析逻辑在 plugins/cm510_parser.py。
"""
from plugins.cm510_parser import CM510Parser as CM510Plugin

__all__ = ["CM510Plugin"]
