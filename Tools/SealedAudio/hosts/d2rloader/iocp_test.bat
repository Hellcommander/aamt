@echo off
rem Builds iocp_test.exe (the core + a completion-port reader, see iocp_test.cpp) with the d2r key, into obj\iocp_test.
rem   iocp_test.bat [core source folder]     default: ..\..\src
setlocal
set "HERE=%~dp0"
set "CORE=%HERE%..\.."
set "SRC=%~1"
if "%SRC%"=="" set "SRC=%CORE%\src"
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
call "%VCVARS%" >nul || exit /b 1
set "OBJ=%CORE%\obj\iocp_test"
if not exist "%OBJ%" mkdir "%OBJ%"
python "%CORE%\..\Shared\audio_seal.py" write-cpp-key "%OBJ%\SealedKey.h" --game d2r --namespace SealedKey || exit /b 1
cl /nologo /std:c++20 /O2 /W4 /EHsc /MT /DNDEBUG /DWIN32_LEAN_AND_MEAN /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS ^
   /I "%OBJ%" /I "%CORE%\include" /I "%SRC%" /Fo"%OBJ%\\" /Fe"%OBJ%\iocp_test.exe" ^
   "%HERE%iocp_test.cpp" "%SRC%\Archives.cpp" "%SRC%\CrashLog.cpp" "%SRC%\FileHooks.cpp" "%SRC%\Log.cpp" "%SRC%\sealed_audio_api.cpp" ^
   /link /NOLOGO psapi.lib dbghelp.lib bcrypt.lib || exit /b 1
