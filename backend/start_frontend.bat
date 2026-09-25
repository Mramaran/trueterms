@echo off
title TrueTerms - Frontend
color 0B
echo.
echo ========================================
echo   TrueTerms - Frontend
echo   http://localhost:3000
echo ========================================
echo.
cd /d "%~dp0..\frontend"
echo Starting React frontend...
npm run dev
pause
