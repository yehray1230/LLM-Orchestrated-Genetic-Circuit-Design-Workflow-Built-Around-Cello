@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%CD%\venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo.
    echo [ERROR] The project virtual environment was not found:
    echo         %PYTHON%
    echo.
    echo Create it and install the project dependencies first. See QUICKSTART.md.
    echo.
    pause
    exit /b 1
)

"%PYTHON%" -m scripts.launch_web_workspace
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo The Web Workspace could not be started.
    echo Review the message above, then press any key to close this window.
    pause >nul
)

exit /b %EXIT_CODE%
