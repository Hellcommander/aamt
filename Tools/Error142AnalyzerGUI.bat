@echo off
cd /d "%~dp0"
if exist "TerrariaMods\bin\Debug\net8.0-windows\Error142AnalyzerGUI.exe" (
    "TerrariaMods\bin\Debug\net8.0-windows\Error142AnalyzerGUI.exe"
) else (
    echo Building Error142AnalyzerGUI...
    dotnet build Error142AnalyzerGUI.csproj
    if exist "TerrariaMods\bin\Debug\net8.0-windows\Error142AnalyzerGUI.exe" (
        "TerrariaMods\bin\Debug\net8.0-windows\Error142AnalyzerGUI.exe"
    ) else (
        echo Build failed. Running from source...
        dotnet run --project Error142AnalyzerGUI.csproj
    )
)
pause
