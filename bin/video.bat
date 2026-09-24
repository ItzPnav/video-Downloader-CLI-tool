@echo off
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\src"
python -W ignore "%ROOT%\src\main.py" %*
if %ERRORLEVEL% equ 9009 (
    py -W ignore "%ROOT%\src\main.py" %*
)
