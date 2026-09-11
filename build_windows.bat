@echo off
REM ===================================================================
REM  VisManager - Windows build script
REM  Double-click this file, or run it from PowerShell / cmd.
REM  Output: dist\VisManager.exe
REM ===================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ============================================
echo   VisManager - building Windows executable
echo  ============================================
echo.

REM ---- Locate Python -------------------------------------------------
set PY=
where py >nul 2>&1 && set PY=py
if "%PY%"=="" ( where python >nul 2>&1 && set PY=python )
if "%PY%"=="" (
    echo  [ERROR] Python was not found on your PATH.
    echo          Install it from https://python.org and tick
    echo          "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)
echo  [1/4] Using Python: %PY%
%PY% --version

REM ---- Dependencies --------------------------------------------------
echo.
echo  [2/4] Installing dependencies...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Dependency install failed.
    pause
    exit /b 1
)

REM ---- Clean -------------------------------------------------------
echo.
echo  [3/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM ---- Build ---------------------------------------------------------
REM  NOTE: the module is "PyInstaller" with capital P and I.
REM  "python -m pyinstaller" (lowercase) fails with ModuleNotFoundError
REM  even when the package is correctly installed.
echo.
echo  [4/4] Building executable (this takes a minute)...
%PY% -m PyInstaller vismanager.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. Scroll up for the cause.
    pause
    exit /b 1
)

echo.
if exist dist\VisManager.exe (
    echo  ============================================
    echo   SUCCESS
    echo  ============================================
    echo.
    echo   Your executable:   dist\VisManager.exe
    for %%A in (dist\VisManager.exe) do echo   Size:              %%~zA bytes
    echo.
    echo   This single file is self-contained - copy it
    echo   anywhere. The build\ folder is scratch work
    echo   and can be deleted.
    echo.
) else (
    echo  [WARNING] Build reported success but dist\VisManager.exe
    echo            is missing. Check the log above.
)
pause
