@echo off
rem TX Test Bot: starts Transcendence in test mode with lowered settings, runs the bot, restores settings, writes a report.
rem Extra arguments go to tx_testbot.py, e.g.  RunTestBot.bat --hops 5 --adventure 0x900000
cd /d "%~dp0"
python -I tx_testbot.py %*
echo.
pause
