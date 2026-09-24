@echo off
title MacroPad Web Dashboard & Terminal Debugger
echo ================================================================
echo   STARTING MACROPAD REAL-TIME TERMINAL & DIAGNOSTIC DASHBOARD
echo ================================================================
echo.
echo Opening browser at http://localhost:5000 ...
start http://localhost:5000
echo.
python app.py
pause
