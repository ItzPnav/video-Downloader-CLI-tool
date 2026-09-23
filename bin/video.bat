@echo off
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\src"
python -W ignore "%ROOT%\src\main.py" %*
