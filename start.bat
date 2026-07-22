@echo off
chcp 65001 >nul 2>&1
echo.
echo ========================================
echo   洞察者 AI - 智能财报分析助手
echo ========================================
echo.

:: 激活虚拟环境
echo [1/3] 激活项目环境...
FOR /F "tokens=*" %%i IN ('poetry env info --path') DO (
    CALL "%%i\Scripts\activate.bat"
)

:: 启动后端服务
echo [2/3] 启动后端服务 (端口 8000)...
start "洞察者AI后端" cmd /c "uvicorn financial_report_ai_assistant.api.main:app --host 127.0.0.1 --port 8000 --app-dir src"

:: 等待服务就绪后打开浏览器
echo [3/3] 等待服务就绪...
:WAIT_LOOP
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 goto WAIT_LOOP

echo.
echo ✅ 服务已启动！正在打开浏览器...
start http://127.0.0.1:8000/

echo.
echo ========================================
echo   浏览器已打开 http://127.0.0.1:8000
echo   关闭此窗口不会停止后端服务
echo   如需停止服务，请关闭"洞察者AI后端"窗口
echo ========================================
echo.
pause
