@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0generation\serve_workbench.py" --ensure --open
    if errorlevel 1 pause
    exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0generation\serve_workbench.py" --ensure --open
    if errorlevel 1 pause
    exit /b
)
echo Python 3 is required. Please open this project in its configured Python environment.
pause
