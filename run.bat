@echo off
setlocal
title ViralCutter

cd /d "%~dp0"
echo Activating virtual environment and starting CLI...
call .venv\Scripts\activate.bat
python main_improved.py
echo.
pause
