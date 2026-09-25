@echo off
title TrueTerms - Uvicorn API Server
color 0A
echo.
echo ========================================
echo   TrueTerms - Uvicorn API Server
echo   http://localhost:8000
echo ========================================
echo.
rem Project root = the folder above this script, wherever it lives
cd /d "%~dp0.."
echo Starting FastAPI backend...
python -m uvicorn backend.api_server:app --port 8000
pause
