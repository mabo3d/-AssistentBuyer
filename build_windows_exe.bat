@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo AssistentBuyer v1.0 - portable Windows EXE bauen
echo ============================================================
echo.
if not exist ".buildvenv\Scripts\python.exe" (
  echo [1/4] Build-Umgebung...
  py -m venv .buildvenv || goto :error
)
echo [2/4] Build-Abhaengigkeiten...
".buildvenv\Scripts\python.exe" -m pip install -q -r requirements-build.txt || goto :error
echo [3/4] PyInstaller...
".buildvenv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile ^
  --name AssistentBuyer ^
  --add-data "static;static" ^
  --add-data "data;data" ^
  --collect-all uvicorn ^
  app.py || goto :error
echo [4/4] Fertig.
echo.
echo Portable EXE:
echo %CD%\dist\AssistentBuyer.exe
echo.
echo Lokal starten:
echo   AssistentBuyer.exe
echo.
echo Fuer andere PCs/iPads im LAN (nur wenn Firmenrichtlinien es erlauben):
echo   AssistentBuyer.exe --lan
echo.
pause
exit /b
:error
echo.
echo BUILD FEHLGESCHLAGEN.
echo Keine Adminrechte sind normalerweise erforderlich, aber Python/Paketinstallation
echo oder Endpoint-Security koennen durch Firmenrichtlinien blockiert sein.
pause
