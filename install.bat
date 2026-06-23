@echo off
chcp 65001 >nul
echo ============================================
echo  SEB Agent - Installing / Updating packages
echo ============================================
echo.
pip uninstall -y google-generativeai 2>nul
pip install -r requirements.txt
echo.
echo ============================================
echo  Done! Run start.bat to launch the agent.
echo ============================================
pause
