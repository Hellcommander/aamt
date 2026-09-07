@echo off
REM Start-StableDiffusionServer.bat
REM Batch wrapper for Start-StableDiffusionServer.ps1
REM
REM No trailing `pause`: the PS1 launches the server DETACHED and returns once
REM it is responding. A pause here used to show "Press any key to continue"
REM and dismissing it closed the console (killing a server attached to it).

setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-StableDiffusionServer.ps1" %*

endlocal
exit /b %ERRORLEVEL%
