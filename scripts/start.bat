@echo off
chcp 65001 >nul
echo Starting SEB Bot...
cd /d "%~dp0.."
python main.py
pause
