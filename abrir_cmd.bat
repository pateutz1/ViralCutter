@echo off

REM Go to the folder where this .bat lives
cd /d "%~dp0"

REM Activate the virtual environment created by uv
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Virtual environment .venv activated.
) else (
    echo WARNING: Virtual environment .venv not found.
    echo Run install_dependencies.bat first.
)

REM Open an interactive CMD and keep it open
cmd /k
