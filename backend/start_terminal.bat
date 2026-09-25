@echo off
title TrueTerms - Python Terminal
color 0E
echo.
echo ========================================
echo   TrueTerms - Python Terminal
echo   Use this for pip installs,
echo   running scripts, ingestion etc.
echo ========================================
echo.
rem The backend folder (this script's folder), where query.py and run_ingestion.py live
cd /d "%~dp0"
echo Ready! Some useful commands:
echo.
echo   python query.py "what is PAM contract"
echo   python run_ingestion.py
echo   pip install -r requirements.txt
echo.
cmd /k
