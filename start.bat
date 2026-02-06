@echo off
echo Activating project environment...

:: Get the virtual environment path and call the activate script
FOR /F "tokens=*" %%i IN ('poetry env info --path') DO (
    CALL "%%i\Scripts\activate.bat"
)

echo.
echo Environment activated!
echo Launching VS Code...

:: 使用 START 命令在一个新进程中打开 VS Code，避免与当前终端窗口关联
start "" code .

echo.
echo All done. You can now use this activated terminal.
cmd /k