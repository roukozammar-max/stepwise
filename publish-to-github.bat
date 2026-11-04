@echo off
setlocal
cd /d "%~dp0"
set "REPO_URL=https://github.com/roukozammar-max/stepwise.git"
if not exist "verifier\.venv\Scripts\python.exe" (
  echo  Stepwise isn't set up yet. Double-click setup.bat first.
  echo.
  pause
  exit /b 1
)
echo.
echo  Uploading Stepwise to GitHub
echo  ============================
echo.
"verifier\.venv\Scripts\python.exe" tools\publish_github.py %REPO_URL% --name "Ammar Roukoz" --email "334105805+roukozammar-max@users.noreply.github.com"
echo.
pause
