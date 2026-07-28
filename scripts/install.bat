@echo off
chcp 65001 >nul
echo ============================================
echo  SEB Bot - Installing / Updating packages
echo ============================================
echo.
cd /d "%~dp0.."
pip uninstall -y google-generativeai 2>nul
pip install -r requirements.txt
echo.
echo ============================================
echo  Done! Run scripts\start.bat to launch the agent.
echo ============================================
pause
