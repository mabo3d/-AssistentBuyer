@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv || goto :error
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error
".venv\Scripts\python.exe" app.py --lan
exit /b
:error
echo.
echo AssistentBuyer konnte nicht gestartet werden.
pause
