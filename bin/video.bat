@echo off
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\src"
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -W ignore "%ROOT%\src\main.py" %*
) else (
    python -W ignore "%ROOT%\src\main.py" %*
)
