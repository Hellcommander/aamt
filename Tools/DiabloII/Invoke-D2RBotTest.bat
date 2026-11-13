@echo off
rem Usage: Invoke-D2RBotTest.bat <script file> [more Invoke-D2RBotTest.ps1 arguments]
rem Runs the script in the game at D:\games\Diablo II Resurrected.
if "%~1"=="" (
    echo Usage: %~nx0 ^<script file^> [-TimeoutSec 300] [-Mod D2RMM] [-NoWait]
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Invoke-D2RBotTest.ps1" -Root "D:\games\Diablo II Resurrected" -Script %*
exit /b %ERRORLEVEL%
