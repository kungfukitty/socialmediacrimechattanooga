@echo off
REM Keeps running: one cycle every few minutes (set loop_minutes in autopost_config.json).
REM Close this window or press Ctrl + C to stop.
cd /d "%~dp0"
python autopost.py --loop
pause
