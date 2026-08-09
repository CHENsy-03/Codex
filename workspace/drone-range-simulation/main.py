"""无人机二维航程计算样品 - 应用入口。

TASK-001：仅创建 QApplication、主窗口并进入事件循环。
"""

import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())