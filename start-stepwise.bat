@echo off
setlocal
cd /d "%~dp0"
if not exist "verifier\.venv\Scripts\python.exe" (
  echo  Stepwise isn't set up yet. Double-click setup.bat first.
  echo.
  pause
  exit /b 1
)
echo.
echo  Starting Stepwise
echo  =================
echo.
"verifier\.venv\Scripts\python.exe" tools\start_web.py
echo.
pause
