@echo off
REM ====================================================================
REM  CampusDesk — one-click launcher for Windows
REM  Team: Team Anonymous
REM ====================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ================================================================
echo    CampusDesk  -  College Information ^& Document Platform
echo    Team: Team Anonymous
echo  ================================================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM --- Create venv ---
if not exist ".venv" (
    echo  [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo  [1/4] Virtual environment already exists.
)

call .venv\Scripts\activate.bat

REM --- Install deps ---
echo  [2/4] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- .env ---
if not exist ".env" (
    echo  [3/4] Creating .env from .env.example ...
    copy .env.example .env >nul
) else (
    echo  [3/4] .env already exists.
)

REM --- Start ---
echo  [4/4] Starting CampusDesk server...
echo.
echo  ----------------------------------------------------------------
echo   Open your browser at:  http://localhost:5000
echo.
echo   Demo logins  (password: password123)
echo     Admin           : admin
echo     Teacher         : teacher1
echo     Student (CSE A2): CSE2024001
echo     Student (CSE A1): CSE2024003
echo     Student (CS  A2): CS2024001
echo     Student (AI  A1): AI2024001
echo.
echo   Press CTRL+C to stop the server.
echo  ----------------------------------------------------------------
echo.

start "" http://localhost:5000
python run.py

pause
endlocal
