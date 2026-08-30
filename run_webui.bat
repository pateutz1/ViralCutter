@echo off
echo Activating virtual environment and starting WebUI...
call .venv\Scripts\activate.bat
python webui\app.py
echo.
pause
