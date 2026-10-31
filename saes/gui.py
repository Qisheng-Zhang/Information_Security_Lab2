"""兼容 GUI 导入路径，默认使用 Qt 工作台。"""

from .qt_gui import SaesWindow, create_application, main

SaesApp = SaesWindow

if __name__ == "__main__":
    raise SystemExit(main())
