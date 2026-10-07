@echo off
chcp 65001 >nul 2>&1
echo.
echo ========================================
echo   预下载 Docker 构建大文件（torch CUDA）
echo ========================================
echo.
echo 下载完成后，docker compose build 会直接使用本地文件，不再走网络。
echo 不下载也能构建，只是 torch 会在构建时下载（较慢）。
echo.

cd /d "%~dp0"

echo [1/2] 定位 Python / Poetry 环境...
set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
    where poetry >nul 2>&1 && set "PY_CMD=poetry run python"
)
if not defined PY_CMD (
    echo [错误] 未找到 python 或 poetry，请先安装 Python 3.11+ 。
    echo        也可以手动执行：python scripts\download_docker_wheels.py
    pause
    exit /b 1
)

echo [2/2] 开始下载（支持断点续传，已存在的文件会自动跳过）...
%PY_CMD% scripts\download_docker_wheels.py

echo.
if errorlevel 1 (
    echo [失败] 下载未成功完成，请检查网络后重新运行本脚本。
) else (
    echo [完成] wheel 已保存到 docker\wheels\ ，可以执行：
    echo        docker compose up --build
)
echo.
pause
