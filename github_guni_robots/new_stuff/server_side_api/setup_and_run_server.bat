@echo off
echo ========================================
echo Robot Face API Server Setup Script
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists, removing old one...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/4] Installing dependencies...
python -m pip install --upgrade pip

REM Install from requirements.txt if it exists, otherwise install manually
if exist "requirements.txt" (
    echo Installing from requirements.txt...
    pip install -r requirements.txt
) else (
    echo Installing dependencies manually...
    pip install fastapi uvicorn python-multipart
    pip install requests elevenlabs groq python-dotenv
    pip install pyttsx3 paho-mqtt
)

if errorlevel 1 (
    echo ERROR: Failed to install some dependencies
    echo Continuing anyway...
)

echo [4/4] Checking for server.py...
if not exist "server.py" (
    echo ERROR: server.py file not found in current directory
    echo Please make sure server.py is in the same folder as this script
    pause
    exit /b 1
)

echo ========================================
echo Setup complete! Starting server...
echo ========================================
echo Server will run on: http://localhost:8001
echo Press Ctrl+C to stop the server
echo ========================================

python server.py

echo ========================================
echo Server stopped
echo ========================================
pause
