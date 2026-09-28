@echo off
setlocal
cd /d "%~dp0\.."
echo.
echo ================================================================
echo   CampusDesk - Reset Database
echo ================================================================
echo WARNING: Deletes current database and uploads.
echo.
pause
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
python scripts\reset.py
pause
endlocal
