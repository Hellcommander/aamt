# Terraria Mod Analysis Tools

This directory contains tools for analyzing tModLoader mods, now with drag-and-drop GUI support!

## Tools Available

### Error 142 Analyzer
**Static analysis tool** to find potential Error 142 causes in tModLoader mod source code.
- **Console**: `Error142Analyzer.exe <mod-source-path>`
- **GUI**: `Error142AnalyzerGUI.bat` or `Error142AnalyzerGUI.exe`
  - Drag and drop a mod source folder onto the window
  - Or click Browse to select a folder
  - Click Analyze to run the analysis

### Error 142 Simulator
**Simulates tModLoader's mod loading process** to detect Error 142 by actually loading types.
- **Console**: `Error142Simulator.exe <mod-source-path> <tmodloader-source-path>`
- **GUI**: `Error142SimulatorGUI.bat` or `Error142SimulatorGUI.exe`
  - Drag and drop a mod source folder onto the window
  - Browse to select tModLoader source folder (or use default if available)
  - Click Simulate to run the simulation

### WorldGen Simulator
**Analyzes mod worldgen conflicts** to help determine which mods should be isolated to subworlds.
- **Console**: `WorldGenSimulator.exe <mod-source-path>` or `WorldGenSimulator.exe --all`
- **GUI**: `WorldGenSimulatorGUI.bat` or `WorldGenSimulatorGUI.exe`
  - Drag and drop a mod source folder onto the window
  - Or click Browse to select a folder
  - Choose "Execute mode" for more accurate (but slower) analysis
  - Click "Analyze Selected" for single mod or "Analyze All Mods" for all mods

## Building the Tools

All tools are .NET 8.0 projects. To build:

```bash
# Build all tools
dotnet build Error142Analyzer.csproj
dotnet build Error142Simulator.csproj
dotnet build WorldGenSimulator.csproj

# Build GUI versions
dotnet build Error142AnalyzerGUI.csproj
dotnet build Error142SimulatorGUI.csproj
dotnet build WorldGenSimulatorGUI.csproj
```

## Running the GUI Tools

### Option 1: Use Batch Files
Double-click the `.bat` files:
- `Error142AnalyzerGUI.bat`
- `Error142SimulatorGUI.bat`
- `WorldGenSimulatorGUI.bat`

### Option 2: Run Directly
```bash
dotnet run --project Error142AnalyzerGUI.csproj
dotnet run --project Error142SimulatorGUI.csproj
dotnet run --project WorldGenSimulatorGUI.csproj
```

### Option 3: Build and Run Executables
After building, run the `.exe` files from the `bin/Debug/net8.0-windows/` directory.

## Drag and Drop Support

All GUI tools support drag and drop:
1. Open the GUI tool
2. Drag a mod source folder from Windows Explorer
3. Drop it onto the gray drop zone
4. The path will be automatically filled
5. Click the Analyze/Simulate button to run

## Console Mode

All tools still support console mode when command-line arguments are provided:
- If you run the GUI executable with arguments, it will run in console mode instead
- This allows integration with scripts and automation

## Requirements

- .NET 8.0 SDK
- tModLoader.dll (referenced from Steam installation)
- Mono.Cecil package (automatically restored)
- Ionic.Zlib package (automatically restored)

## File Locations

All tool source files are now in the root `Tools` folder:
- `Error142Analyzer.cs` - Static analyzer
- `Error142Simulator.cs` - Type loading simulator
- `WorldGenSimulator.cs` - Worldgen conflict analyzer
- `WorldGenExecutionSimulator.cs` - Execution-based worldgen analyzer
- `TmodFileReader.cs` - .tmod file reader
- `MultiModWorldGenAnalyzer.cs` - Multi-mod analyzer

GUI wrappers:
- `Error142AnalyzerGUI.cs` - GUI for Error142Analyzer
- `Error142SimulatorGUI.cs` - GUI for Error142Simulator
- `WorldGenSimulatorGUI.cs` - GUI for WorldGenSimulator
