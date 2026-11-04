@echo off
setlocal
cd /d "%~dp0"
echo.
echo  Stepwise setup
echo  ==============
echo.

rem Find Python 3.10+: first the "py" launcher (preferring tested versions),
rem then "python" on PATH, then a per-user python.org install.
set "PYEXE="
set "PYARGS="
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not defined PYEXE (
    py -%%V -c "import sys" >nul 2>&1 && (set "PYEXE=py" & set "PYARGS=-%%V")
  )
)
if not defined PYEXE (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1 && set "PYEXE=python"
)
for %%V in (313 312 311 310) do (
  if not defined PYEXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
  )
)
if not defined PYEXE goto nopython

:havepython
"%PYEXE%" %PYARGS% tools\setup_dev.py
echo.
pause
exit /b

:nopython
echo  Python 3.10 or newer isn't installed on this computer (or Windows can't find it).
echo.
where winget >nul 2>&1
if errorlevel 1 goto manualpython
choice /C YN /M " Install Python 3.13 now (about 2 minutes)"
if errorlevel 2 goto manualpython
winget install -e --id Python.Python.3.13 --scope user
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
  set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  set "PYARGS="
  echo.
  echo  Python is installed. Continuing with the setup...
  echo.
  goto havepython
)
echo.
echo  If the install finished, close this window and double-click setup.bat again.
pause
exit /b

:manualpython
echo  Install Python from https://www.python.org/downloads/
echo  On the first screen of the installer, tick "Add python.exe to PATH".
echo  Then double-click setup.bat again.
echo.
pause
exit /b
