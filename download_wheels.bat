@echo off
chcp 65001 >nul
echo ========================================
echo  预下载 Docker 构建依赖（torch CUDA wheel）
echo ========================================
echo.

set WHEEL_DIR=%~dp0docker\wheels
set WHEEL_FILE=torch-2.10.0+cu126-cp311-cp311-manylinux_2_28_x86_64.whl
set URL=https://mirrors.aliyun.com/pytorch-wheels/cu126/torch-2.10.0%%2Bcu126-cp311-cp311-manylinux_2_28_x86_64.whl

if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%"

if exist "%WHEEL_DIR%\%WHEEL_FILE%" (
    echo ✅ 文件已存在: %WHEEL_FILE%
    echo    跳过下载
    goto :done
)

echo ⬇️  正在下载 torch CUDA wheel (841MB)...
echo    保存到: %WHEEL_DIR%\%WHEEL_FILE%
echo.

REM 优先用 curl（Windows 10/11 自带），速度快
where curl >nul 2>nul
if %errorlevel%==0 (
    echo 使用 curl 下载...
    curl -L -# -o "%WHEEL_DIR%\%WHEEL_FILE%" "%URL%"
    if %errorlevel%==0 goto :done
    echo curl 下载失败，尝试 PowerShell...
)

REM 备用：PowerShell
echo 使用 PowerShell 下载...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%URL%' -OutFile '%WHEEL_DIR%\%WHEEL_FILE%' }"
if %errorlevel%==0 goto :done

echo ❌ 下载失败，请手动下载：
echo    %URL%
echo    保存到: %WHEEL_DIR%\%WHEEL_FILE%
pause
exit /b 1

:done
echo.
echo ========================================
echo  ✅ 下载完成！
echo ========================================
echo.
echo  下一步：运行 docker-compose build
echo.
pause
