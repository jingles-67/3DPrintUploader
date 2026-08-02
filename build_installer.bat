@echo off
setlocal

set /p APP_VERSION=<"%~dp0VERSION"
if not defined APP_VERSION (
    echo VERSION is missing or empty.
    exit /b 1
)

set "MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe"
if exist "%MAKENSIS%" goto build

set "MAKENSIS=C:\Program Files\NSIS\makensis.exe"
if exist "%MAKENSIS%" goto build

set "MAKENSIS=%LOCALAPPDATA%\Programs\NSIS\makensis.exe"
if exist "%MAKENSIS%" goto build

echo NSIS was not found. Install NSIS 3 and run this file again.
exit /b 1

:build
"%MAKENSIS%" /V4 /DAPP_VERSION=%APP_VERSION% /DAPP_VERSION_4=%APP_VERSION%.0 "%~dp0installer\3DPrintUploader.nsi"
if errorlevel 1 exit /b %errorlevel%

echo.
echo Installer created: %~dp0dist\3D Print Uploader Setup.exe
exit /b 0
