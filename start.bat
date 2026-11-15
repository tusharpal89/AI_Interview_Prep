@echo off
REM ===== PrepPilot (AI Interview Prep) launcher =====
REM Double-click to start. Opens backend + frontend in their own windows,
REM then opens the app in your browser.

cd /d "%~dp0"

echo Starting backend (http://localhost:8001) ...
start "PrepPilot Backend" cmd /k "venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001"

echo Starting frontend (http://localhost:5174) ...
start "PrepPilot Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for the servers to warm up ...
timeout /t 8 /nobreak >nul

start "" http://localhost:5174

echo.
echo ================================================================
echo  PrepPilot is starting - it will open in your browser shortly.
echo  Keep the two new windows open while you use the app.
echo  Close them to stop PrepPilot.
echo ================================================================
echo.
pause
