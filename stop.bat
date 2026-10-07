@echo off
setlocal
chcp 65001 >nul 2>&1
title AI Financial Report Assistant - Stop

echo.
echo ========================================================
echo   Stopping the service on port 8000
echo ========================================================
echo.

powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if($c){$c|ForEach-Object{Write-Host ('killing pid '+$_.OwningProcess);Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue}}else{Write-Host 'nothing listening on port 8000'}"

echo.
echo Done. Close any backend console window that is still open.
pause
