@echo off
cd /d "%~dp0"
if exist "TerrariaMods\bin\Debug\net8.0-windows\WorldGenSimulatorGUI.exe" (
    "TerrariaMods\bin\Debug\net8.0-windows\WorldGenSimulatorGUI.exe"
) else (
    echo Building WorldGenSimulatorGUI...
    dotnet build WorldGenSimulatorGUI.csproj
    if exist "TerrariaMods\bin\Debug\net8.0-windows\WorldGenSimulatorGUI.exe" (
        "TerrariaMods\bin\Debug\net8.0-windows\WorldGenSimulatorGUI.exe"
    ) else (
        echo Build failed. Running from source...
        dotnet run --project WorldGenSimulatorGUI.csproj
    )
)
pause
