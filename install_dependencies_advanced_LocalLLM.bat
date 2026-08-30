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
    echo Installing LLaMA C++ for NVIDIA...
    uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
) else (
    echo.
    echo Installing PyTorch and ONNX for AMD/CPU...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
    uv pip install onnxruntime==1.20.1
    echo Installing standard LLaMA C++ (Requires C++ Build Tools)...
    uv pip install llama-cpp-python
)

echo.
echo ==========================================
echo Installing ALL dependencies (INCLUDING LOCAL LLM MODELS)
echo Warning: This takes longer. Requires C++ Build Tools.
echo ==========================================
uv pip install -r requirements.txt

echo.
echo ==========================================
echo Done! ViralCutter is ready to run Local Models.
echo ==========================================
pause
