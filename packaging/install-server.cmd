@echo off
setlocal
"%~dp0bin\bash.exe" /install-server.sh %*
exit /b %errorlevel%
