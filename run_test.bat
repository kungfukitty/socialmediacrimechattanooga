@echo off
REM Safe test: pull the 911 list and make videos into the output folder, but upload nothing.
cd /d "%~dp0"
python autopost.py --once --dry-run
explorer output
pause
