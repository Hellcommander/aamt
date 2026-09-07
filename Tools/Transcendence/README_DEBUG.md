# Debug Logging

The tool now creates a debug log file at:
```
Extensions/Tools/tool_debug.log
```

This log file tracks:
- Path parameter values received
- Path resolution attempts
- Success/failure of path setting
- Any errors during path processing

## To view the log:

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
Get-Content tool_debug.log -Tail 50
```

Or open it in Notepad:
```cmd
notepad tool_debug.log
```

## To clear the log:

```powershell
Remove-Item tool_debug.log -ErrorAction SilentlyContinue
```

The log will be recreated the next time you run the tool.

