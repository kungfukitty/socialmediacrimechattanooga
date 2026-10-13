@echo off
REM One cycle: pull the 911 list, make videos for new newsworthy calls, upload them.
cd /d "%~dp0"
python autopost.py --once
pause
