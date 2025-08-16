@echo off
echo Activating project environment...

:: Get the virtual environment path and call the activate script
FOR /F "tokens=*" %%i IN ('poetry env info --path') DO (
    CALL "%%i\Scripts\activate.bat"
)

echo.
echo Environment activated! Welcome back.
echo You are now in the project shell.

:: Start a new command prompt session within the activated environment
cmd /k