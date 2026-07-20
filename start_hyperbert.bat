@echo off
title HyperBERT Launcher
color 0A

echo.
echo  ============================================
echo    HyperBERT - One-Click Launcher
echo  ============================================
echo.

:: Start backend in background
echo  [1/3] Starting backend server...
start /B cmd /c "cd /d %~dp0 && python backend/app.py" > nul 2>&1
timeout /t 3 /nobreak > nul

:: Start frontend in background
echo  [2/3] Starting frontend dev server...
start /B cmd /c "cd /d %~dp0\frontend && npm run dev" > nul 2>&1
timeout /t 4 /nobreak > nul

:: Open browser
echo  [3/3] Opening browser...
start http://localhost:5173
echo.
echo  ============================================
echo   Servers are running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:5000
echo.
echo   AI model is loading in the background.
echo   The upload page will show a green dot
echo   when the model is ready (~2-3 min).
echo.
echo   Press Ctrl+C or close this window to stop.
echo  ============================================
echo.

:: Keep window alive and poll status
:loop
timeout /t 10 /nobreak > nul
curl -s http://localhost:5000/api/status 2>nul | findstr "true" > nul
if %errorlevel% equ 0 (
    echo  [OK] AI model is now ready! Analysis will be fast.
    echo.
) 
goto loop
