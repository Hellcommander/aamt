# Virtual File System (VFS) Asset Generation Guide

Generate visual assets for the Virtual File System including file type icons, directory/folder icons, archive icons, mount/unmount indicators, VFS status indicators, cache status indicators, and file browser UI elements.

## Quick Start

```powershell
# Generate all VFS assets
.\GenerateVFSAssets.ps1

# Use C++ backend for better quality
.\GenerateVFSAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### File Type Icons (7 icons)

1. **file_generic** - Generic file icon
2. **file_text** - Text file icon
3. **file_json** - JSON file icon
4. **file_lua** - Lua file icon
5. **file_image** - Image file icon
6. **file_audio** - Audio file icon
7. **file_binary** - Binary file icon

### Directory/Folder Icons (4 icons)

1. **folder_generic** - Generic folder icon
2. **folder_open** - Open folder icon
3. **folder_root** - Root folder icon
4. **folder_mounted** - Mounted folder icon

### Archive Icons (3 icons)

1. **archive_generic** - Generic archive icon
2. **archive_zip** - ZIP archive icon
3. **archive_mounted** - Mounted archive icon

### Mount/Unmount Indicators (4 indicators)

1. **mount_mounted** - Mounted indicator
2. **mount_unmounted** - Unmounted indicator
3. **mount_button** - Mount button icon
4. **unmount_button** - Unmount button icon

### VFS Status Indicators (5 indicators)

1. **status_ready** - VFS ready indicator
2. **status_indexing** - Indexing indicator
3. **status_index_valid** - Index valid indicator
4. **status_index_invalid** - Index invalid indicator
5. **status_error** - VFS error indicator

### Cache Status Indicators (5 indicators)

1. **cache_enabled** - Cache enabled indicator
2. **cache_disabled** - Cache disabled indicator
3. **cache_hit** - Cache hit indicator
4. **cache_miss** - Cache miss indicator
5. **cache_full** - Cache full indicator

### File Browser UI Elements (6 elements)

1. **ui_panel_browser** - File browser panel background
2. **ui_panel_mounts** - Mounts panel background
3. **ui_button_refresh** - Refresh button icon
4. **ui_button_rebuild_index** - Rebuild index button icon
5. **ui_button_clear_cache** - Clear cache button icon
6. **ui_button_search** - Search button icon

## Total: ~34 Assets

## Output Structure

```
assets/
└── vfs/
    ├── file_types/
    │   ├── file_generic.png
    │   ├── file_text.png
    │   └── ... (all file type icons)
    ├── directories/
    │   ├── folder_generic.png
    │   ├── folder_open.png
    │   └── ... (all directory icons)
    ├── archives/
    │   ├── archive_generic.png
    │   ├── archive_zip.png
    │   └── ... (all archive icons)
    ├── mount/
    │   ├── mount_mounted.png
    │   ├── mount_unmounted.png
    │   └── ... (all mount indicators)
    ├── status/
    │   ├── status_ready.png
    │   ├── status_indexing.png
    │   └── ... (all status indicators)
    ├── cache/
    │   ├── cache_enabled.png
    │   ├── cache_disabled.png
    │   └── ... (all cache indicators)
    └── ui/
        ├── ui_panel_browser.png
        ├── ui_button_refresh.png
        └── ... (all UI elements)
```

## Integration

### VirtualFileSystem

```cpp
// Mount directory
VirtualFileSystem::getInstance().mount("/path/to/directory", priority);
// Uses: /assets/vfs/mount/mount_mounted.png
// Uses: /assets/vfs/directories/folder_mounted.png

// Mount archive
VirtualFileSystem::getInstance().mountArchive("/path/to/archive.zip", priority);
// Uses: /assets/vfs/mount/mount_mounted.png
// Uses: /assets/vfs/archives/archive_mounted.png

// Open file
auto file = VirtualFileSystem::getInstance().open("/path/to/file.json");
// Uses: /assets/vfs/file_types/file_json.png

// Check if index is valid
bool valid = VirtualFileSystem::getInstance().isIndexValid();
// Uses: /assets/vfs/status/status_index_valid.png
// or: /assets/vfs/status/status_index_invalid.png

// Get stats
auto stats = VirtualFileSystem::getInstance().getStats();
// Uses: /assets/vfs/cache/cache_enabled.png
// Uses: /assets/vfs/cache/cache_hit.png
// Uses: /assets/vfs/cache/cache_miss.png
```

### VFSIndex

```cpp
// Build index
index.buildIndex();
// Uses: /assets/vfs/status/status_indexing.png

// Find file
auto location = index.findFile("/path/to/file");
// Uses: /assets/vfs/file_types/file_*.png
```

## File Types

### Supported File Types
- **Generic**: Unknown file type
- **Text**: Text documents
- **JSON**: JSON configuration files
- **Lua**: Lua scripts
- **Image**: Image files
- **Audio**: Audio files
- **Binary**: Binary files

## Directory States

### Directory Types
- **Generic**: Standard directory
- **Open**: Currently open directory
- **Root**: Root directory
- **Mounted**: Mounted directory source

## Archive Types

### Archive Types
- **Generic**: Unknown archive type
- **ZIP**: ZIP archive files
- **Mounted**: Mounted archive source

## Mount States

### Mount States
- **Mounted**: Source is mounted
- **Unmounted**: Source is not mounted

## VFS Status

### Status Types
- **Ready**: VFS is ready for operations
- **Indexing**: Building file index
- **Index Valid**: Index is valid and up-to-date
- **Index Invalid**: Index needs rebuilding
- **Error**: VFS error occurred

## Cache Status

### Cache States
- **Enabled**: Cache is enabled
- **Disabled**: Cache is disabled
- **Hit**: Cache hit (file found in cache)
- **Miss**: Cache miss (file not in cache)
- **Full**: Cache is full

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateVFSAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure VFS

Set up VirtualFileSystem with asset paths (if UI is implemented).

### Step 3: Mount Sources

```cpp
auto& vfs = VirtualFileSystem::getInstance();
vfs.mount("/path/to/directory", 0);
vfs.mountArchive("/path/to/archive.zip", 1);
```

### Step 4: Use VFS

```cpp
// Read file
auto data = vfs.readFile("/path/to/file.json");

// Check if file exists
bool exists = vfs.exists("/path/to/file");

// List files
auto files = vfs.listFiles("/path/to/directory");
```

### Step 5: Test in Game

Load the mod and test VFS system in-game (if UI is implemented).

## Advanced Options

### Custom File Types

Edit `GenerateVFSAssets.ps1` to add custom file type icons.

### Custom Directory Types

Add custom directory types as needed.

### Custom Archive Types

Add custom archive types with unique icons.

## Tips

1. **File type icons**: Use 32x32 for file type icons
2. **Directory icons**: Use 32x32 for directory icons
3. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
4. **UI buttons**: Use 32x32 for buttons
5. **Status indicators**: Make status indicators clear and recognizable
6. **Cache indicators**: Keep cache indicators simple

## Troubleshooting

### Icons Not Displaying

- Check file type icon paths
- Verify icons are in `assets/vfs/file_types/`
- Ensure VFS UI is properly configured

### Mount Indicators Not Showing

- Check mount indicator paths
- Verify indicators are in `assets/vfs/mount/`
- Ensure mount system is enabled

### Status Not Displaying

- Check status indicator paths
- Verify indicators are in `assets/vfs/status/`
- Ensure status system is enabled

### Cache Indicators Not Working

- Check cache indicator paths
- Verify indicators are in `assets/vfs/cache/`
- Ensure cache system is enabled

## Note

The VFS is primarily a backend system. These assets are for potential future UI implementations such as:
- File browser interface
- Mount management UI
- VFS status display
- Cache management interface

If no UI is planned, these assets may not be necessary.

---

*Part of the Starbound Ollama Asset Generator suite*
