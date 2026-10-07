@echo off
setlocal
chcp 65001 >nul 2>&1
title AI Financial Report Assistant - Launcher

echo.
echo ========================================================
echo   AI Financial Report Assistant
echo   Backend :  http://127.0.0.1:8000
echo   API docs:  http://127.0.0.1:8000/docs
echo ========================================================
echo.

rem ---- 0. project root ----
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

rem ---- 1. locate the python interpreter ----
rem      plain .venv first, then ask poetry as a fallback.
set "VENV_PY=%PROJECT_DIR%.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    for /f "tokens=" %%i in ('poetry env info --path 2^>nul') do set "VENV_PY=%%i\Scripts\python.exe"
)
if not exist "%VENV_PY%" (
    echo [1/5] ERROR: no python environment found.
    echo        Fix: poetry install
    echo.
    pause
    exit /b 1
)
echo [1/5] Interpreter: %VENV_PY%

rem ---- 2. .env file ----
if exist "%PROJECT_DIR%.env" (
    echo [2/5] .env found
) else if exist "%PROJECT_DIR%env.template" (
    copy /y "env.template" ".env" >nul
    echo [2/5] .env created from env.template.
) else (
    echo [2/5] WARNING: no .env file, AI answers will fail.
)

rem placeholder key check - catches the copied template
findstr /i /l /c:"sk-your-deepseek-api-key" ".env" >nul 2>&1
if not errorlevel 1 (
    echo        !!! .env still holds the PLACEHOLDER key !!!
    echo        Fix now: edit .env, set DEEPSEEK_API_KEY=sk-REAL-KEY
    echo        The service will start, but EVERY ai answer fails with 401.
    echo.
    pause
)

rem ---- 3. proxy: localhost must never go through the proxy ----
set "NO_PROXY=127.0.0.1,localhost,::1"
set "no_proxy=127.0.0.1,localhost,::1"

rem ---- 4. already running? ----
curl -s -m 2 --noproxy '*' -o nul "http://127.0.0.1:8000/health" >nul 2>&1
if not errorlevel 1 (
    echo [4/5] Port 8000 already serving.
    goto OPEN_BROWSER
)

echo [4/5] starting backend (a new console window will open)...
start "AI Financial Report Assistant - Backend" "%VENV_PY%" -m uvicorn financial_report_ai_assistant.api.main:app --host 127.0.0.1 --port 8000 --app-dir src

rem ---- 5. wait until /health answers ----
echo [5/5] waiting for the service to be ready.
set "TRY=0"
:WAIT_LOOP
set /a "TRY+=1"
timeout /t 1 /nobreak >nul
curl -s -m 2 --noproxy '*' -o nul "http://127.0.0.1:8000/health" >nul 2>&1
if not errorlevel 1 goto WAIT_OK

if %TRY% GEQ 60 (
    echo.
    echo [ERROR] service did not answer in 60s.
    echo         Check the backend console window, or run:
    echo           .venv\Scripts\python.exe -m uvicorn financial_report_ai_assistant.api.main:app --app-dir src
    echo.
    pause
    exit /b 1
)
goto WAIT_LOOP

:WAIT_OK
curl -s -m 3 --noproxy '*' "http://127.0.0.1:8000/health"

:OPEN_BROWSER
echo.
start "" "http://127.0.0.1:8000/"
echo ========================================================
echo   Running. Close the BACKEND window to stop it.
echo   Or run: stop.bat
echo ========================================================
echo.
pause
