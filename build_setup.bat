@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\CineTrack\CineTrack.exe" (
    echo Missing dist\CineTrack\CineTrack.exe. Run build.bat first.
    exit /b 1
)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
)

if not defined ISCC (
    echo Inno Setup 6 compiler was not found.
    echo Install Inno Setup 6 or add ISCC.exe to PATH, then retry.
    exit /b 1
)

echo Compiling installer with:
echo %ISCC%
"%ISCC%" /Qp installer.iss
if errorlevel 1 (
    echo Installer compilation failed.
    exit /b 1
)

if exist "Output\CineTrack_Setup.exe" (
    echo.
    echo Installer created: Output\CineTrack_Setup.exe
) else (
    echo Compiler returned success, but Output\CineTrack_Setup.exe was not found.
    exit /b 1
)
exit /b 0
