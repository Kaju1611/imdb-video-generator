@echo off
echo ============================================================
echo   IMDb Video Generator - Windows Setup
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Download from https://www.python.org/downloads/
    echo         Check "Add Python to PATH" during install.
    pause & exit /b 1
)
echo [OK] Python found.

ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] FFmpeg not found. Install via:
    echo   winget install --id Gyan.FFmpeg
    echo   OR download from https://www.gyan.dev/ffmpeg/builds/
    echo   and add C:\ffmpeg\bin to your PATH.
    echo.
) else ( echo [OK] FFmpeg found. )

echo.
echo [Setup] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo [OK] Packages installed.

if not exist .env ( copy .env.example .env >nul && echo [Setup] Created .env - add your API keys. )

echo.
echo ============================================================
echo   Done! Next steps:
echo   1. Open .env and fill in your API keys
echo   2. Double-click run.bat to generate a video
echo ============================================================
pause
