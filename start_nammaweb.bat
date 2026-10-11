@echo off
title NammaWeb AI

echo ========================================
echo        NAMMAWEB AI STARTING
echo ========================================

echo.
echo [1/3] Checking Ollama...

ollama list >nul 2>&1

if errorlevel 1 (
    echo Ollama is not running. Starting Ollama...
    start "" ollama serve
    echo Waiting for Ollama...
    timeout /t 5 /nobreak >nul
) else (
    echo Ollama is already running.
)

echo.
echo [2/3] Starting Streamlit...

call "%~dp0venv\Scripts\activate.bat"

start "" "%~dp0venv\Scripts\python.exe" -m streamlit run "%~dp0app.py" --server.address 127.0.0.1 --server.port 8502 --server.fileWatcherType none

echo.
echo [3/3] Opening NammaWeb AI...

timeout /t 4 /nobreak >nul

start "" http://localhost:8502

echo.
echo ========================================
echo        NammaWeb AI is running
echo Local: http://localhost:8502
echo ========================================

pause