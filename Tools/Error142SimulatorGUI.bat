@echo off
cd /d "%~dp0"
if exist "TerrariaMods\bin\Debug\net8.0-windows\Error142SimulatorGUI.exe" (
    "TerrariaMods\bin\Debug\net8.0-windows\Error142SimulatorGUI.exe"
) else (
    echo Building Error142SimulatorGUI...
    dotnet build Error142SimulatorGUI.csproj
    if exist "TerrariaMods\bin\Debug\net8.0-windows\Error142SimulatorGUI.exe" (
        "TerrariaMods\bin\Debug\net8.0-windows\Error142SimulatorGUI.exe"
    ) else (
        echo Build failed. Running from source...
        dotnet run --project Error142SimulatorGUI.csproj
    )
)
pause
