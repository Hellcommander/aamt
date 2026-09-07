# ToME Asset Generator Logger Guide

## Overview

All ToME asset generators use a centralized logging system for consistent issue tracking and debugging. This logger writes to both timestamped log files and a "latest.log" file for easy access.

## Log Files

Logs are stored in the `logs/` directory:

- **Timestamped logs**: `logs/tome_asset_generator_YYYYMMDD_HHMMSS.log`
  - One log file per session
  - Contains full detailed logs with timestamps
  - Useful for historical tracking

- **Latest log**: `logs/latest.log`
  - Always contains the most recent session's log
  - Overwritten on each new session
  - Quick access to current issues

## Log Levels

The logger uses standard Python logging levels:

- **DEBUG**: Detailed information for diagnosing problems
  - Asset generation details
  - AI request/response details
  - File operations
  - Performance metrics

- **INFO**: General informational messages
  - Generation start/end
  - Progress updates
  - Important state changes

- **WARNING**: Warning messages
  - Non-critical issues
  - Fallback behaviors
  - Missing optional features

- **ERROR**: Error messages
  - Failed operations
  - Exceptions (with tracebacks)
  - Critical issues

- **CRITICAL**: Critical errors
  - System failures
  - Unrecoverable errors

## Usage in Generators

### Basic Usage

```python
from tome_asset_generator_logger import get_logger, log_exception, log_generation_start

# Get a logger
logger = get_logger("MyGenerator")

# Log messages
logger.info("Starting generation...")
logger.debug("Detailed debug information")
logger.warning("Warning message")
logger.error("Error message")

# Log exceptions
try:
    # Some code
    pass
except Exception as e:
    log_exception(e, "context description")
```

### Convenience Functions

```python
from tome_asset_generator_logger import (
    info, debug, warning, error, critical,
    log_generation_start, log_generation_end,
    log_asset_generation, log_ai_request,
    log_file_operation, log_performance
)

# Simple logging
info("Information message")
debug("Debug message")
warning("Warning message")
error("Error message")

# Structured logging
log_generation_start("GeneratorName", "mod-name", {"config": "value"})
log_asset_generation("asset_name", 1, 10, 85.5)
log_generation_end("GeneratorName", results_dict)
```

### Specialized Logging Functions

```python
# AI operations
log_ai_request("TASK_VISUAL", "Generate color palette", "WizardLM")
log_ai_response("TASK_VISUAL", "Generated palette: ...", "WizardLM")

# File operations
log_file_operation("copy", Path("source.png"), Path("dest.png"))
log_file_operation("delete", Path("old.png"))

# Performance
log_performance("asset_generation", 12.5, {"variations": 100, "assets": 10})
```

## Log Format

### Console Output (INFO and above)
```
2024-01-15 14:30:45 | INFO     | Starting Asset Generation
2024-01-15 14:30:46 | WARNING  | AI model not available, using fallback
2024-01-15 14:30:50 | ERROR    | Failed to generate asset: timeout
```

### File Output (All levels, detailed)
```
2024-01-15 14:30:45.123 | INFO     | ToMEAssetGenerator | log_generation_start:42 | Starting Asset Generation
2024-01-15 14:30:45.124 | INFO     | ToMEAssetGenerator | log_generation_start:43 | Generator: RatlichAssetGenerator
2024-01-15 14:30:45.125 | INFO     | ToMEAssetGenerator | log_generation_start:44 | Mod: ratlich-race
2024-01-15 14:30:46.200 | DEBUG    | ToMEAssetGenerator | generate:150 | Generating asset: base_body_front
2024-01-15 14:30:46.201 | DEBUG    | ToMEAssetGenerator | log_ai_request:95 | AI Request - Type: TASK_VISUAL, Model: WizardLM
```

## Integration Examples

### In Generator Classes

```python
from tome_asset_generator_logger import get_logger, log_exception, log_generation_start, log_generation_end

class MyGenerator:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def generate(self):
        log_generation_start("MyGenerator", "my-mod", {"variations": 10})
        try:
            # Generation code
            results = {}
            log_generation_end("MyGenerator", results)
        except Exception as e:
            log_exception(e, "asset generation")
            raise
```

### In GUI Applications

```python
from tome_asset_generator_logger import get_logger, log_exception

class MyGUI:
    def __init__(self):
        self.logger = get_logger("MyGUI")
    
    def on_generate(self):
        try:
            self.logger.info("User clicked generate button")
            # Generation code
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            log_exception(e, "GUI generation")
            messagebox.showerror("Error", str(e))
```

## Troubleshooting

### Finding Issues

1. **Check latest.log first**: `logs/latest.log` contains the most recent session
2. **Search for ERROR/CRITICAL**: Look for error messages
3. **Check exception tracebacks**: Full stack traces are logged at DEBUG level
4. **Review AI requests**: Check if AI calls are failing
5. **Check file operations**: Verify file paths and permissions

### Common Issues

**"File not found" errors:**
- Check log for file paths
- Verify paths are correct
- Check file permissions

**AI model failures:**
- Check `log_ai_request` and `log_ai_response` entries
- Verify Ollama is running
- Check model availability

**Performance issues:**
- Look for `log_performance` entries
- Check duration of operations
- Identify bottlenecks

**Generation failures:**
- Check exception tracebacks
- Review asset generation logs
- Verify generator configuration

## Log File Management

### Automatic Cleanup

The logger creates new timestamped files for each session. Old log files are not automatically deleted, but you can:

1. **Manual cleanup**: Delete old log files periodically
2. **Keep recent logs**: Keep last N days of logs
3. **Archive important logs**: Move logs to archive before deletion

### Log File Size

- Each log file can grow large with many assets
- Consider rotating logs if they exceed reasonable size
- Latest.log is overwritten each session (no size issue)

### Best Practices

1. **Always log exceptions**: Use `log_exception()` for proper traceback logging
2. **Log important state changes**: Generation start/end, configuration changes
3. **Use appropriate log levels**: DEBUG for details, INFO for progress, ERROR for problems
4. **Include context**: Add context strings to exception logs
5. **Check logs regularly**: Review logs to identify patterns or recurring issues

## Example Log Analysis

### Successful Generation
```
INFO | Starting Asset Generation
INFO | Generator: RatlichAssetGenerator
INFO | Mod: ratlich-race
DEBUG | Generating asset: base_body_front - Variation 1/100
DEBUG | Generating asset: base_body_front - Variation 2/100
...
INFO | Asset Generation Complete
INFO | Results: 15 assets generated
```

### Failed Generation
```
INFO | Starting Asset Generation
ERROR | Exception occurred in asset generation: FileNotFoundError: [Errno 2] No such file or directory: 'source.png'
DEBUG | Traceback:
DEBUG |   File "generate_ratlich_assets.py", line 150, in generate
DEBUG |     shutil.copy2(source, dest)
DEBUG | ...
CRITICAL | Generation failed completely
```

### AI Issues
```
DEBUG | AI Request - Type: TASK_VISUAL, Model: WizardLM
WARNING | AI model not available, using fallback
DEBUG | AI Response - Type: TASK_VISUAL, Model: fallback
```

## Integration Checklist

When adding logging to a new generator:

- [ ] Import logger at the top: `from tome_asset_generator_logger import get_logger`
- [ ] Create logger instance: `self.logger = get_logger(self.__class__.__name__)`
- [ ] Log generation start: `log_generation_start(...)`
- [ ] Log generation end: `log_generation_end(...)`
- [ ] Wrap exceptions: `try/except` with `log_exception(...)`
- [ ] Log important operations: file operations, AI calls, etc.
- [ ] Test logging: Verify logs are created and readable

