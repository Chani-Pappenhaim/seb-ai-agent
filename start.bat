@echo off
chcp 65001 >nul
echo Starting SEB Agent...
cd /d "%~dp0"
python main.py
pause
