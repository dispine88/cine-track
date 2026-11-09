@echo off
echo =========================================
echo CLEANING OLD BUILD FILES...
echo =========================================
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CineTrack.spec del CineTrack.spec

echo.
echo =========================================
echo BUILDING EXE (PyInstaller)...
echo =========================================
py -m PyInstaller --noconfirm --onedir --windowed --name "CineTrack" --add-data "style.qss;." main.py

echo.
echo =========================================
echo DONE! EXE IS IN dist\CineTrack
echo NOW OPEN INNO SETUP AND PRESS F9
echo =========================================
pause