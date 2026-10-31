"""Qt 图形界面入口；优先使用已准备好的项目虚拟环境。"""

import importlib.util
import os
from pathlib import Path
import sys


def main():
    if importlib.util.find_spec("PySide6") is None:
        root = Path(__file__).resolve().parent
        local_python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if local_python.is_file() and local_python.resolve() != Path(sys.executable).resolve():
            os.execv(str(local_python), [str(local_python), str(Path(__file__).resolve()), *sys.argv[1:]])
        print("请先双击启动程序.bat，或在虚拟环境中运行 pip install -r requirements.txt。")
        return 1
    from saes.qt_gui import main as qt_main

    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main())
