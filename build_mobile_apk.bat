@echo off
setlocal
title Build JARVIS Mobile APK
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot"
set "PATH=%JAVA_HOME%\bin;%PATH%"
cd /d "%~dp0mobile"
C:\src\flutter\bin\cache\dart-sdk\bin\dart.exe C:\src\flutter\bin\cache\flutter_tools.snapshot build apk
echo.
echo APK output:
echo %CD%\build\app\outputs\flutter-apk\app-release.apk
pause
