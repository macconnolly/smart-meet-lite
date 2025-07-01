@echo off
echo Starting Smart-Meet Lite...
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Check if Qdrant is running
docker ps | findstr "smart-meet-lite-qdrant" >nul
if errorlevel 1 (
    echo Starting Qdrant database...
    docker-compose up -d
    echo Waiting for Qdrant to initialize...
    timeout /t 5 /nobreak >nul
)

REM Start the API
echo.
echo Starting API server...
echo.
echo ========================================
echo Smart-Meet Lite is starting...
echo API: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo ========================================
echo.

python -m src.api
