@echo off
set /p url="Enter TikTok Profile URL: "
echo Starting scan...
python src/main.py "%url%"
pause
