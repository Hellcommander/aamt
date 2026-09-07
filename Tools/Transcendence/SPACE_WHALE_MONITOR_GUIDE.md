# Space Whale Asset Generator - Control Room Monitor Guide

## Overview

The Control Room Monitor is a WPF-based GUI tool that shows **live spritesheet previews** in per-job cards as model/build jobs complete. Each job card displays:

- **Left Panel**: Live spritesheet preview image (thumbnail)
- **Right Panel**: Real-time logs and console output
- **Progress Bar**: Shows completion percentage
- **Status Text**: Current job status
- **Controls**: Open Folder, Cancel buttons

## Features

### Per-Job Cards

Each generation task gets its own card:
- **Visual Language Assets**: Monitors `VisualLanguage/` directory
- **FX Assets**: Monitors `FX/` directory  
- **Audio Assets**: Monitors `Audio/` directory
- **Texture Generation**: Monitors `Textures/` directory
- **Spritesheet (120 Facings)**: Monitors `Spritesheets/` directory

### Live Preview System

- **Automatic Detection**: Uses `FileSystemWatcher` to detect new files as they're written
- **Image Loading**: Loads preview images using `BitmapImage` with `CacheOption=OnLoad` (allows file to be overwritten)
- **Thumbnail Display**: Shows 200x200px preview in each job card
- **Real-time Updates**: Updates preview as soon as file is detected

### Progress Tracking

- **Percent Complete**: Updates as files are generated
- **Status Messages**: Shows current stage (e.g., "File detected", "Preview loaded", "Spritesheet complete!")
- **Log Streaming**: Real-time console output in expandable log panel

## Usage

### Basic Launch

```powershell
powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1 -WatchDirectory "Output" -MaxCores 32
```

### With Test Samples

```batch
TestMonitorWithSamples.bat
```

This will:
1. Generate test sample images
2. Launch the monitor GUI
3. Display the samples in job cards

### During Generation

The monitor can be launched **while generation is in progress**. It will:
- Detect existing files and load them as previews
- Monitor for new files as they're created
- Update progress and logs in real-time

## How It Works

### File Detection

1. **FileSystemWatcher** monitors each job's output directory
2. When a file is created or changed, the watcher fires
3. File is checked against job-specific patterns (e.g., `*spritesheet*.png` for spritesheet job)
4. If it matches, the file is loaded as a preview

### Image Loading

```powershell
# Load preview image safely on UI thread
$bi = New-Object System.Windows.Media.Imaging.BitmapImage
$bi.BeginInit()
$bi.CacheOption = 'OnLoad'  # Important: allows file to be overwritten
$bi.UriSource = [Uri]::new($fullPath)
$bi.EndInit()
$bi.Freeze()
$jobVm.PreviewImage = $bi
```

### UI Updates

All UI updates use `Dispatcher.Invoke` to ensure thread safety:
- Progress updates
- Status changes
- Log appending
- Image loading

## Integration with Build Process

### For Real Builds

Replace the simulated job with your actual build process:

1. **Start Build Process**: Use `Start-Process` or `Start-Job` to run your generator
2. **Redirect Output**: Capture stdout/stderr and append to `AppendLog`
3. **Detect Completion**: Watch for final file or parse build output
4. **Update Progress**: Call `Update-JobProgress` as stages complete

### Example Integration

```powershell
# Start Blender export
$process = Start-Process -FilePath "blender" -ArgumentList @(
    "--background",
    "--python", "export_spritesheet.py",
    "--", $outputPath
) -NoNewWindow -PassThru -RedirectStandardOutput $logFile

# Monitor log file
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = Split-Path $logFile -Parent
$watcher.Filter = "*.log"
$watcher.Add_Changed({
    # Parse log and update job progress
    $content = Get-Content $logFile -Tail 10
    $job.AppendLog($content)
    
    # Check for completion
    if ($content -match "Spritesheet saved") {
        $spritesheetPath = Join-Path $outputPath "spritesheet.png"
        Load-PreviewImage -jobVm $job -filePath $spritesheetPath
        Update-JobProgress -Job $job -Percent 100 -Status "Complete!"
    }
})
```

## Troubleshooting

### GUI Not Displaying Visual Elements

**Issue**: Window shows only text, no colors, borders, or progress bars

**Solutions**:
1. **Ensure STA mode**: Script must run with `-STA` flag
   ```powershell
   powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1
   ```
2. **Check WPF assemblies**: Ensure PresentationFramework is loaded
   - Script automatically loads required assemblies
3. **Verify window initialization**: Window should show with dark blue background (#1a2a3a)
4. **Check Application object**: WPF Application is automatically created if needed

**If still not working**:
- Test with `TestMonitorGUI.ps1` to verify WPF is working
- Check Windows version compatibility
- Try running as administrator

### Images Not Showing

- **Check file paths**: Ensure files are being written to monitored directories
- **Check file patterns**: Verify file names match job-specific patterns
- **Check permissions**: Ensure script can read the output files
- **Check file locks**: If build process locks files, write to temp then rename
- **Check image format**: Supported formats: PNG, JPG, BMP
- **Check image size**: Very large images may take time to load

**Error Messages**:
- `Failed to load preview: [error]` - Check file path and format
- `Preview image file not found` - File doesn't exist or path is incorrect
- `Window or Dispatcher not available` - GUI not properly initialized

### Progress Bars Not Visible

**Issue**: Progress bars don't appear or don't update

**Solutions**:
1. **Check data binding**: Progress bars bind to `Percent` property
2. **Verify updates**: Progress updates use `Dispatcher.Invoke`
3. **Check styling**: Progress bars use cyan fill (#66ccff) on dark background
4. **Test with sample data**: Use `TestProgressBars.bat` to verify

**If still not working**:
- Check that `Update-JobProgress` is being called
- Verify `Percent` property is being set correctly
- Check console for binding errors

### UI Not Updating

- **Check STA mode**: Script must run with `-STA` flag
- **Check dispatcher**: All UI updates must use `Dispatcher.Invoke`
- **Check threading**: Background jobs must update UI via dispatcher
- **Check ObservableCollection**: Job collection must be ObservableCollection for automatic UI updates

### Error Handling

The monitor now includes improved error handling:

**Common Errors**:
- **File not found**: Check output directory path
- **Image load failed**: Verify image file is not corrupted
- **Dispatcher error**: GUI not properly initialized (restart script)

**Error Messages Include**:
- File paths for debugging
- File sizes for verification
- Detailed error context

**Recovery**:
- Script continues monitoring even if one image fails to load
- Failed operations are logged but don't stop monitoring
- Check logs in the right panel for detailed error information

### Performance Issues

- **Throttle updates**: Batch log updates (e.g., every 200-500ms)
- **Use thumbnails**: Generate smaller preview images on worker side
- **Limit preview size**: Keep preview images under 512x512px
- **Freeze images**: Always call `Freeze()` on `BitmapImage` after loading

## UX Enhancements

### Future Improvements

- **Animated spinner**: Show spinner overlay while final spritesheet is generating
- **Click to zoom**: Allow clicking preview to open larger viewer
- **Stage timeline**: Show stage timeline above progress bar
- **Resource usage**: Display GPU VRAM usage per job
- **Multiple previews**: Show multiple images per job (e.g., all texture maps)

## Technical Details

### Thread Safety

- **ObservableCollection**: Thread-safe collection for job view models
- **Dispatcher.Invoke**: All UI updates on UI thread
- **FileSystemWatcher**: Events fire on background thread, must use dispatcher

### Memory Management

- **Image caching**: `CacheOption=OnLoad` loads image into memory immediately
- **Freeze images**: `Freeze()` makes image immutable and thread-safe
- **Dispose watchers**: Clean up watchers on window close

### File Watching

- **IncludeSubdirectories**: Watchers monitor subdirectories recursively
- **Multiple events**: Watch both `Created` and `Changed` events
- **Pattern matching**: Filter files by extension and name patterns

## See Also

- `TestMonitorWithSamples.bat` - Test the monitor with sample images
- `CreateQuickTestSamples.py` - Generate test samples
- `test_minimal_space_whale.py` - Automated test suite

