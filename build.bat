@echo off
setlocal
cd /d "%~dp0"

echo =========================================
echo INSTALLING BUILD DEPENDENCIES
echo =========================================
py -m pip install --upgrade -r requirements-build.txt
if errorlevel 1 goto :error

echo.
echo =========================================
echo VERIFYING SOURCE AND TESTS
echo =========================================
py -m compileall -q main.py config.py gui database tests
if errorlevel 1 goto :error
py -m unittest discover -s tests -v
if errorlevel 1 goto :error

echo.
echo =========================================
echo CLEANING PREVIOUS BUILD
echo =========================================
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CineTrack.spec del CineTrack.spec

echo.
echo =========================================
echo BUILDING CINETRACK
echo =========================================
py -m PyInstaller --noconfirm --clean --onedir --windowed --name "CineTrack" --add-data "style.qss;." --collect-all keyring --collect-submodules keyring.backends --copy-metadata keyring main.py
if errorlevel 1 goto :error

echo.
echo Build completed: dist\CineTrack\CineTrack.exe
echo Run build_setup.bat to compile the Inno Setup installer.
pause
exit /b 0

:error
echo.
echo BUILD FAILED. Review the error messages above.
pause
exit /b 1
