@echo off

cd /d "%~dp0"

echo Starting Flight Tracker...
echo.

poetry run python -m app.main

echo.
pause
