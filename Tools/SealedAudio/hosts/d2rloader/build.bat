@echo off
rem Builds sealedaudio.dll, the D2RLoader (Diablo II Resurrected) host of the Sealed Audio core, with the MSVC Build Tools.
rem   build.bat [deploy-folder]
rem The D2RLoader PluginSDK include folder comes from D2RL_SDK, else <game>\mods\SkillTab4\sdk\include (the toolkit's shared
rem copy), else <game>\PluginSDK-master\include; the game folder from D2R_PATH, else the default Steam location.
rem With a deploy folder (a mod's d2rloader\plugins, or <game>\d2rloader\plugins) the dll is copied there.
setlocal
set "HERE=%~dp0"
set "CORE=%HERE%..\.."
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
  echo vcvars64.bat not found
  exit /b 1
)
if "%D2R_PATH%"=="" set "D2R_PATH=D:\games\Steam\steamapps\common\Diablo II Resurrected"
if "%D2RL_SDK%"=="" if exist "%D2R_PATH%\mods\SkillTab4\sdk\include\D2RLPlugin\api.h" set "D2RL_SDK=%D2R_PATH%\mods\SkillTab4\sdk\include"
if "%D2RL_SDK%"=="" if exist "%D2R_PATH%\PluginSDK-master\include\D2RLPlugin\api.h" set "D2RL_SDK=%D2R_PATH%\PluginSDK-master\include"
if not exist "%D2RL_SDK%\D2RLPlugin\api.h" (
  echo D2RLoader PluginSDK not found; set D2RL_SDK to its include folder ^(github.com/D2RLoader/PluginSDK^)
  exit /b 1
)
call "%VCVARS%" >nul || exit /b 1
set "OUT=%CORE%\bin\d2rloader"
set "OBJ=%CORE%\obj\d2rloader"
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%OBJ%" mkdir "%OBJ%"
rem Diablo II Resurrected has its own build key (audio_seal.py --game d2r, made on first use, kept outside the repository);
rem its header is generated into obj\ for this build only. There is no shared key header in src\.
if exist "%CORE%\src\SealedKey.h" (
  echo %CORE%\src\SealedKey.h exists and would override the d2r key: delete it
  exit /b 1
)
python "%CORE%\..\Shared\audio_seal.py" write-cpp-key "%OBJ%\SealedKey.h" --game d2r --namespace SealedKey || exit /b 1
rc /nologo /I "%D2RL_SDK%" /fo "%OBJ%\sealedaudio_d2r.res" "%HERE%sealedaudio_d2r.rc" || exit /b 1
cl /nologo /std:c++20 /O2 /W4 /EHsc /MT /LD /DNDEBUG /DWIN32_LEAN_AND_MEAN /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS ^
   /I "%OBJ%" /I "%CORE%\include" /I "%CORE%\src" /I "%D2RL_SDK%" /Fo"%OBJ%\\" /Fe"%OUT%\sealedaudio.dll" ^
   "%HERE%sealedaudio_d2r.cpp" "%CORE%\src\Archives.cpp" "%CORE%\src\CrashLog.cpp" "%CORE%\src\FileHooks.cpp" ^
   "%CORE%\src\Log.cpp" "%CORE%\src\sealed_audio_api.cpp" "%OBJ%\sealedaudio_d2r.res" ^
   /link /NOLOGO /IMPLIB:"%OBJ%\sealedaudio.lib" psapi.lib dbghelp.lib bcrypt.lib || exit /b 1
echo Built "%OUT%\sealedaudio.dll"
if not "%~1"=="" (
  if not exist "%~1" mkdir "%~1"
  copy /y "%OUT%\sealedaudio.dll" "%~1\" >nul || exit /b 1
  echo Deployed to "%~1"
)
