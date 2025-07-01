@echo off
echo ========================================
echo Smart-Meet Lite - Windows Setup Script
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo.
    echo Creating .env file...
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: Edit .env and add your OpenRouter API key!
    echo Get a key from: https://openrouter.ai/
    notepad .env
    pause
)

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Docker is not installed or not running
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    echo Then run this script again.
    pause
    exit /b 1
)

REM Start Qdrant
echo.
echo Starting Qdrant vector database...
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start Qdrant
    echo Make sure Docker Desktop is running
    pause
    exit /b 1
)

REM Wait for Qdrant to start
echo Waiting for Qdrant to initialize...
timeout /t 5 /nobreak >nul

REM Download model if needed
if not exist "models\onnx\all-MiniLM-L6-v2.onnx" (
    echo.
    echo Downloading ONNX model...
    python scripts\download_model.py
    if errorlevel 1 (
        echo ERROR: Failed to download model
        pause
        exit /b 1
    )
)

REM Initialize database
echo.
echo Initializing database...
python scripts\setup.py
if errorlevel 1 (
    echo ERROR: Failed to initialize database
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start Smart-Meet Lite:
echo 1. Run: python -m src.api
echo 2. Open: http://localhost:8000
echo 3. API docs: http://localhost:8000/docs
echo.
echo To test the system:
echo - Run: python example.py
echo - Run: python bi_demo.py
echo.
pause
