# Logging Guide

## Overview

All asset generation tools now create detailed log files that can be monitored in real-time. Logs are stored in the `Logs` directory with timestamped filenames.

## Log File Locations

- **CDDA Bee Swarm Generator**: `Logs\CDDABeeSwarm_YYYYMMDD_HHMMSS.log`
- **Asset Generator Control Room**: `Logs\AssetGeneratorControlRoom_YYYYMMDD_HHMMSS.log`

## Log Format

Each log entry follows this format:
```
[YYYY-MM-DD HH:MM:SS.fff] [LEVEL] Message
```

### Log Levels

- **INFO**: General information and progress updates
- **SUCCESS**: Successful operations completed
- **WARN**: Warnings (non-critical issues)
- **ERROR**: Errors that prevented completion

## Viewing Logs

### PowerShell - View Latest Log

```powershell
# View latest CDDA log
Get-ChildItem "Logs" -Filter "CDDABeeSwarm_*.log" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 | 
    ForEach-Object { Get-Content $_.FullName -Tail 50 }
```

### PowerShell - Monitor Log in Real-Time

```powershell
# Watch log file as it's being written
$logFile = Get-ChildItem "Logs" -Filter "CDDABeeSwarm_*.log" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 -ExpandProperty FullName

Get-Content $logFile -Wait -Tail 20
```

### PowerShell - Search Logs

```powershell
# Find all errors in logs
Get-ChildItem "Logs" -Filter "*.log" | 
    Select-String "\[ERROR\]" | 
    Select-Object -First 20
```

## Log File Information

The log file path is displayed:
- In the console output when generation starts
- In the Control Room status bar
- At the end of generation output

## Example Log Output

```
[2025-12-29 12:11:35.226] [INFO] ═══════════════════════════════════════════════════════════
[2025-12-29 12:11:35.233] [INFO]   CDDA Bee Swarm Creature Generator
[2025-12-29 12:11:35.236] [INFO] Log file: D:\...\Logs\CDDABeeSwarm_20251229_121135.log
[2025-12-29 12:11:35.245] [INFO] Swarm Name: test_swarm
[2025-12-29 12:11:35.253] [INFO] Generating bee swarm sprites...
[2025-12-29 12:11:35.294] [INFO]   Generating: test_swarm_N_idle
[2025-12-29 12:11:35.429] [SUCCESS] Generated 24 sprites
[2025-12-29 12:11:35.438] [SUCCESS]   Bee Swarm Generation Complete
```

## Tips

1. **Check logs immediately**: The log file is created at the very start of generation, so you can monitor it from the beginning.

2. **Filter by level**: Use `Select-String` to filter by log level:
   ```powershell
   Get-Content $logFile | Select-String "\[ERROR\]"
   ```

3. **Compare logs**: Keep multiple log files to compare different generation runs.

4. **Log rotation**: Old logs are kept indefinitely. You can manually clean up old logs if needed:
   ```powershell
   # Delete logs older than 30 days
   Get-ChildItem "Logs" -Filter "*.log" | 
       Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
       Remove-Item
   ```

## Integration with Control Room

When the Control Room GUI is launched, it also creates a log file. The log file path is shown in the status bar at the bottom of the window.

All GUI actions (button clicks, file detections, preview updates) are logged with timestamps for debugging.

