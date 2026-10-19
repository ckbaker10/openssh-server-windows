@echo off
setlocal
"%~dp0bin\bash.exe" --noprofile --norc /open-shell.sh %*
exit /b %errorlevel%
