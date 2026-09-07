# Logger Integration Summary

## Overview

A centralized logging system has been created for all ToME asset generators. This document summarizes what was created and how to integrate it into existing generators.

## Created Files

1. **`tome_asset_generator_logger.py`** - Main logger module
   - Singleton logger instance
   - Timestamped log files + latest.log
   - Structured logging functions
   - Exception logging with tracebacks

2. **`TOME_LOGGER_GUIDE.md`** - Complete usage guide
   - Detailed documentation
   - Examples and best practices
   - Troubleshooting guide

3. **Updated `generate_ratlich_assets.py`** - Example integration
   - Shows how to use logger in generators
   - Logs generation start/end
   - Logs exceptions and performance

## Quick Integration Steps

### 1. Import the Logger

```python
from tome_asset_generator_logger import (
    get_logger, log_exception, log_generation_start, log_generation_end,
    log_asset_generation, log_file_operation, log_performance
)
import time
```

### 2. Initialize Logger in Class

```python
class MyGenerator:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # ... rest of init
```

### 3. Log Generation Start

```python
def generate(self):
    log_generation_start("MyGenerator", "mod-name", {"config": "value"})
    start_time = time.time()
    # ... generation code
```

### 4. Log Exceptions

```python
try:
    # code that might fail
    pass
except Exception as e:
    log_exception(e, "context description")
    raise  # or handle appropriately
```

### 5. Log Generation End

```python
    duration = time.time() - start_time
    log_performance("generate_all", duration, {"assets": len(results)})
    log_generation_end("MyGenerator", results)
    return results
```

## Generators to Update

The following generators should be updated to use the logger:

### High Priority (Main Generators)
- [x] `generate_ratlich_assets.py` - ✅ Already updated
- [ ] `tome_asset_generator_ai.py` - Core AI generator
- [ ] `tome_asset_generator.py` - Base generator
- [ ] `tome_asset_generator_extended.py` - Extended generator

### Medium Priority (CLI Tools)
- [ ] `tomegen_cli.py` - Base CLI
- [ ] `tomegen_extended_cli.py` - Extended CLI
- [ ] `tomegen_ai_cli.py` - AI CLI

### Low Priority (GUI Tools)
- [ ] `tome_asset_generator_gui.py` - Main GUI
- [ ] `generate_ratlich_assets_gui.py` - Ratlich GUI
- [ ] `tome_mod_checker.py` - Mod checker
- [ ] `tome_mod_checker_gui.py` - Mod checker GUI

### Utility Scripts
- [ ] `extract_talents.py` - Talent extractor
- [ ] `extract_glutton_talents.py` - Glutton extractor
- [ ] `extract_ratlich_talents.py` - Ratlich extractor
- [ ] `update_ratlich_race_assets.py` - Asset updater

## Integration Checklist

For each generator, add:

- [ ] Import logger module
- [ ] Create logger instance in `__init__`
- [ ] Log initialization (success/failure)
- [ ] Log generation start with config
- [ ] Log exceptions with context
- [ ] Log file operations (copy, delete, etc.)
- [ ] Log AI requests/responses (if applicable)
- [ ] Log performance metrics
- [ ] Log generation end with results
- [ ] Test logging output

## Example Integration

See `generate_ratlich_assets.py` for a complete example of logger integration.

Key patterns:
- Logger instance in `__init__`
- `log_generation_start()` at beginning
- `log_exception()` in try/except blocks
- `log_file_operation()` for file ops
- `log_performance()` for timing
- `log_generation_end()` at completion

## Log File Locations

- **Timestamped logs**: `logs/tome_asset_generator_YYYYMMDD_HHMMSS.log`
- **Latest log**: `logs/latest.log`

All generators write to the same log files, making it easy to track issues across the entire system.

## Benefits

1. **Centralized Issue Tracking**: All generators log to the same system
2. **Easy Debugging**: Full tracebacks and context for errors
3. **Performance Monitoring**: Track generation times
4. **AI Request Tracking**: Monitor AI model usage
5. **File Operation Audit**: Track all file operations
6. **Historical Logs**: Timestamped logs for each session

## Next Steps

1. Update core generators (`tome_asset_generator_ai.py`, etc.)
2. Update CLI tools
3. Update GUI tools
4. Update utility scripts
5. Test all generators with logging enabled
6. Review logs to identify common issues

## Notes

- Logger is thread-safe (can be used in GUI threads)
- Logs are UTF-8 encoded (supports all characters)
- Console output shows INFO and above
- File output shows all levels (including DEBUG)
- Latest.log is overwritten each session (no size issues)

