@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Preparing local Python environment...
    python -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import PySide6.QtWidgets" >nul 2>&1
if errorlevel 1 (
    echo Installing Qt interface dependencies...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto failed
)
start "" ".venv\Scripts\pythonw.exe" app.py
exit /b 0
:failed
echo Start failed. Install Python 3.10+ and check the network connection.
pause
exit /b 1
