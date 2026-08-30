@echo off
echo ==========================================
echo Installing uv (fast Python package manager)...
echo ==========================================
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

echo.
echo ==========================================
echo Creating virtual environment (.venv)...
echo ==========================================
:: Try to use uv from PATH. If it fails, you may need to restart the terminal.
uv venv

echo.
echo ==========================================
echo GPU CONFIGURATION
echo ==========================================
echo What is your graphics card?
echo [1] NVIDIA (Install with CUDA acceleration - Faster)
echo [2] AMD / None (Or if unsure - Install normal version)
set /p gpu_choice="Choose (1/2): "

if "%gpu_choice%"=="1" (
    echo.
    echo Installing PyTorch and ONNX for NVIDIA...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
    uv pip install onnxruntime-gpu==1.20.1
) else (
    echo.
    echo Installing PyTorch and ONNX for AMD/CPU...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
    uv pip install onnxruntime==1.20.1
)

echo.
echo ==========================================
echo Installing essential dependencies from requirements.txt...
echo (Cloud AIs / No Local Models)
echo ==========================================
:: Activates the venv temporarily for the install (uv manages this automatically if it detects the venv)
:: If uv venv created the .venv folder, uv pip install will use it by default from the project root.
uv pip install -r requirements.txt

echo.
echo ==========================================
echo Done!
echo ==========================================
pause
