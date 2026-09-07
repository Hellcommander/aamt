# Transcendence Mod Tools - Changelog

## Version 4.9 - Smart Drag-and-Drop with Auto-Detection

### 🎯 Major Feature

#### 1. Drag-and-Drop Support 🎨
Drop files or folders directly onto the tool window:
- ✅ **Single XML files** - Quick validate
- ✅ **Mod folders** - Full project analysis
- ✅ **Multiple files** - Batch processing
- ✅ **Resource files** - Image/sound detection

#### 2. Smart Auto-Detection 🧠
Automatic analysis of dropped content:
- ✅ **File type detection** - XML, folder, image, sound
- ✅ **API version check** - Detects outdated APIs
- ✅ **Deprecated function scan** - Flags old API usage
- ✅ **Issue detection** - BOM, raw `>`, parentheses
- ✅ **Health score** - 0-100 overall quality score

#### 3. Recommended Actions 💡
Context-aware action suggestions:
- ✅ **Quick Validate** - Run XML/TLisp checks
- ✅ **Fix Errors** - Auto-fix detected issues
- ✅ **Check Deprecated API** - Semantic validation
- ✅ **Full Health Report** - Comprehensive analysis
- ✅ **Dependency Graph** - Visualize relationships
- ✅ **Cross-Mod Compatibility** - UNID conflict check

#### 4. Smart Detection Dialog 🎭
Interactive popup with:
- ✅ **Mod name and type**
- ✅ **API version status** (Current/Outdated/Legacy)
- ✅ **Health score** with color coding
- ✅ **Issue summary** (errors, warnings)
- ✅ **One-click action buttons**
- ✅ **Full report option**

### 📊 API Version Detection

| API | Status | Action |
|-----|--------|--------|
| 57 | ✅ Current | No action needed |
| 56 | ⚠ Outdated | Consider updating |
| 55 | ⚠ Outdated | Update required |
| 50-54 | ⚠ Legacy | Major update required |
| 20-25 | ❌ Ancient | Complete rewrite may be needed |

### 🔍 Deprecated Function Detection

Automatically detects deprecated API 57 functions:
- `objAddItem` → `objAddItemByValue`
- `objRemoveItem` → `objRemoveItemByValue`
- `shpOrder` → `objSendMessage`
- `sysCreateWeaponFire` → `objFireWeapon`
- `itmGetArmorType` → `itmGetArmorClass`
- `rollDice` → `mathRandom`

### 🎨 Health Score

Score calculation:
- Start at 100
- -15 per error
- -5 per warning
- -1 per info
- -10 for outdated API
- -25 for legacy API
- -50 for ancient API

Color coding:
- 🟢 80-100: Healthy
- 🟡 50-79: Needs attention
- 🔴 0-49: Requires fixes

### 💡 Recommended Actions by Context

**Single XML File**:
1. Quick Validate
2. Fix Errors (if any)
3. Review Warnings

**Mod Folder**:
1. Quick Validate
2. Full Health Report
3. Dependency Graph
4. Cross-Mod Compatibility
5. Check Deprecated API

**Outdated API**:
1. Check Deprecated API
2. Semantic Validation

### 🔧 Technical Details

- **Module Size**: ~18KB
- **Detection Time**: <1 second for most mods
- **Functions**: 7+ functions for detection/analysis
- **Rule Format**: Extensible deprecated function list
- **UI Framework**: WinForms drag-and-drop

### 🎮 How to Use

1. **Drag** a file or folder onto the tool window
2. **View** the Smart Detection dialog
3. **Click** a recommended action
4. **Tool** automatically navigates to correct tab and runs action

Or click "Skip to Normal Menu" to manually browse.

---

## Version 4.8 - Live Preview of Resolved Types

### 🔥 Killer Feature

#### 1. Live Type Preview 🎯
Click a type and see everything about it:
- ✅ **Fully Resolved Attributes** - After inheritance resolution
- ✅ **All Events** - Implemented and inherited events
- ✅ **All Resources** - Images, sounds, icons
- ✅ **All References** - Types this type uses/inherits/spawns
- ✅ **Referenced By** - Types that reference this type
- ✅ **Override Conflicts** - Attribute conflicts with parents

#### 2. Comprehensive Type Information 📊
- Type name, UNID, file location
- Attribute sources (Self/Parent)
- Event sources (Self/Parent)
- Resource paths
- Reference relationships
- Reverse reference tracking

#### 3. Interactive Type Selection 🎨
- Load all types from mod
- Dropdown selection
- Instant preview
- Formatted display

### 📊 What It Shows

**Type Information**:
```
Type:      MyShip [ShipClass]
Name:      MyShip
UNID:      0x12345678
File:      MyMod.xml
```

**Resolved Attributes**:
```
level = 5
  Source: Parent: BaseShip
name = My Custom Ship
  Source: Self: MyShip
```

**Events**:
```
OnCreate
  Source: Self: MyShip
OnUpdate
  Source: Parent: BaseShip
```

**Resources**:
```
Images:
  - rsShipImage
Sounds:
  - rsShipSound
```

**References**:
```
Inherits:
  - BaseShip (0x87654321)
Uses:
  - itLaserCannon (0x11111111)
  - svPlayer (0x00000001)
```

**Referenced By**:
```
Used by:
  - MyStation [StationType] (0x22222222)
Inherited by:
  - MyAdvancedShip [ShipClass] (0x33333333)
```

### 🎨 UI Features

- **Mod Path Input**: Select mod folder
- **Load Types Button**: Loads all types from mod
- **Type Dropdown**: Select from all loaded types
- **Preview Button**: Generates comprehensive preview
- **Formatted Display**: Easy-to-read formatted output

### 💡 Use Cases

- **Understand Type Structure**: See all attributes and their sources
- **Debug Inheritance**: See what comes from parent types
- **Track Dependencies**: See what types use this type
- **Find References**: See where this type is used
- **Resource Management**: See all resources used by type
- **Event Analysis**: See all events implemented/inherited

### 🔧 Technical Details

- **Module Size**: ~18KB
- **Functions**: 8+ functions for preview generation
- **Integration**: Uses semantic validation module for inheritance
- **Type Detection**: ItemTypes, ShipClasses, StationTypes, Sovereigns, Missions
- **Resource Detection**: Images, sounds, icons
- **Reference Tracking**: Uses, inherits, spawns relationships
- **Reverse Lookup**: Finds all types that reference target type

### 🎯 Key Features

**Fully Resolved Attributes**:
- Shows all attributes after inheritance resolution
- Indicates source (Self or Parent)
- Shows override conflicts

**Event Tracking**:
- Shows all events (implemented and inherited)
- Indicates event source
- Groups by source

**Resource Discovery**:
- Finds all image references
- Finds all sound references
- Finds all icon references

**Reference Mapping**:
- Shows types this type uses
- Shows inheritance chain
- Shows spawn relationships

**Reverse References**:
- Shows types that use this type
- Shows types that inherit from this type
- Shows types that spawn this type

---

## Version 4.7 - "What Changed?" Diff Mode

### 🎯 Major Feature

#### 1. Diff Mode Comparison 🔍
Compare two versions of a mod or game XML to see:
- ✅ **Added Types** - New ItemTypes, ShipClasses, StationTypes, etc.
- ❌ **Removed Types** - Types that no longer exist
- 🔄 **Changed Types** - Types with modified attributes
- ✅ **Added Events** - New event handlers
- ❌ **Removed Events** - Removed event handlers
- ⚠️ **Deprecated Fields** - Attributes marked as deprecated

#### 2. Attribute Comparison 📊
- Detects added attributes
- Detects removed attributes
- Shows attribute value changes
- Groups changes by type

#### 3. Event Tracking 📝
- Tracks event handler additions
- Tracks event handler removals
- Shows which types have event changes

### 📊 What It Shows

**Summary**:
```
SUMMARY:
  Added Types:        5
  Removed Types:      2
  Changed Types:      8
  Added Events:       12
  Removed Events:     3
  Deprecated Fields:  1
```

**Added Types**:
```
  ✅ MyNewShip [ShipClass]
     UNID: 0x12345678
     File: MyMod.xml
```

**Changed Types**:
```
  🔄 MyShip [ShipClass]
     UNID: 0x12345678
     Attribute Changes:
       ✅ newAttribute = value
       ❌ oldAttribute = value (removed)
       🔄 level: '5' → '7'
```

### 🎨 UI Features

- **Two Path Inputs**: Old version and new version
- **Browse Buttons**: Easy folder selection
- **Compare Button**: Generates comprehensive diff report
- **Detailed Report**: Shows all changes with icons

### 💡 Use Cases

- **Update Mods Between Versions**: See what changed in game XML
- **Track Mod Changes**: Compare mod versions
- **Find Breaking Changes**: Identify removed types/attributes
- **Document Updates**: Generate change logs
- **Debug Issues**: See what changed between working/broken versions

### 🔧 Technical Details

- **Module Size**: ~15KB
- **Functions**: 8+ functions for diff analysis
- **Type Detection**: ItemTypes, ShipClasses, StationTypes, Sovereigns, Missions
- **Attribute Parsing**: Extracts all attributes from type definitions
- **Event Parsing**: Finds all event handlers in types

---

## Version 4.6 - Enhanced Cross-File Dependency Graph

### 🎯 Major Enhancements

#### 1. Comprehensive Node Types 🧭
- ✅ ItemTypes - All item definitions
- ✅ ShipClasses - All ship definitions
- ✅ StationTypes - All station definitions
- ✅ Sovereigns - All sovereign definitions
- ✅ Missions - All mission definitions
- ✅ Tables - Encounter and ship tables

#### 2. Enhanced Relationship Types 🔗
- ✅ **Uses** - Type uses another type (items, weapons, armor, sovereigns)
- ✅ **Spawns** - Type spawns another type (stations spawn ships/encounters)
- ✅ **Overrides** - Type overrides another type (StationTypeOverride)
- ✅ **Inherits** - Type inherits from another type
- ✅ **Calls event on** - Type calls event on another type (objFireEvent, typFireEvent)

#### 3. Enhanced Graph Visualization 📊
- ✅ Graph summary with node/relationship counts
- ✅ Relationship type breakdown
- ✅ Grouped by relationship type
- ✅ Shows event names for "calls event on" relationships
- ✅ Type information in brackets

### 📊 What It Shows

**Graph Summary**:
```
Total Nodes: 45
Total Relationships: 127

Relationship Types:
  calls_event_on: 12
  inherits: 8
  overrides: 3
  spawns: 45
  uses: 59
```

**Relationship Details**:
```
═══════════════════════════════════════════════════════════
USES
═══════════════════════════════════════════════════════════

  MyShip [ShipClass]
    → itLaserCannon [ItemType]

  MyStation [StationType]
    → svPlayer [Sovereign]

═══════════════════════════════════════════════════════════
SPAWNS
═══════════════════════════════════════════════════════════

  MyStation [StationType]
    → MyShip [ShipClass]

  MyStation [StationType]
    → Encounter [Encounter]
```

### 🔍 Relationship Types Explained

**Uses**:
- ShipClass uses ItemType (devices, armor, items)
- StationType uses Sovereign
- ItemType uses ItemType (weapons)

**Spawns**:
- StationType spawns ShipClass
- StationType spawns Encounter
- Table spawns ShipClass

**Overrides**:
- StationTypeOverride overrides StationType
- TypeOverride overrides base type

**Inherits**:
- Type inherits from parent type
- Shows inheritance chain

**Calls event on**:
- Type calls event on another type
- Shows event name (e.g., "OnCreate", "OnUpdate")

### 🎨 UI Features

- **Enhanced Display**: Shows node types and relationship details
- **Summary Section**: Quick overview of graph structure
- **Relationship Breakdown**: Counts by relationship type
- **Type Information**: Shows type in brackets for clarity
- **Event Details**: Shows event names for event calls

### 💡 Benefits

- **Debug Complex Mods**: See all relationships at a glance
- **Balance Spawn Tables**: Visualize what spawns what
- **Track Dependencies**: Understand type dependencies
- **Find Overrides**: See what overrides what
- **Map Event Calls**: See event flow between types

---

## Version 4.5 - TML Static Analysis

### 🎯 Major New Feature

#### 1. Comprehensive TML Code Analysis 🧪
- ✅ Detect unused variables
- ✅ Detect unreachable code in if/switch
- ✅ Warn about expensive operations in frequently-called events
- ✅ Flag deprecated functions
- ✅ Variable usage tracking
- ✅ Control flow analysis

#### 2. TML Analysis UI 📊
- ✅ New "TML Analysis" button in Semantic Validation tab
- ✅ Filter by issue type
- ✅ Color-coded severity levels
- ✅ Double-click to jump to code

#### 3. Analysis Features 🔍

**Unused Variables**:
- Detects variables defined but never used
- Tracks variables in `(block (var1 var2) ...)` and `(setq var value)`
- Ignores function names (obj*, itm*, sys*, etc.)
- Warns about dead code

**Unreachable Code**:
- Detects `(if Nil ...)` - always false
- Detects `(if false ...)` - always false
- Warns about dead code paths

**Expensive Operations**:
- Warns about expensive operations in frequently-called events
- Tracks: OnUpdate, OnDamage, OnFireWeapon, etc.
- Flags: sysFindObject, sysCreateShip, enum, etc.

**Deprecated Functions**:
- Flags deprecated API 57 functions
- Suggests replacements
- Error severity for breaking changes
- Warning severity for deprecated but working

### 📊 What It Detects

**Unused Variables**:
```
⚠ MyMod.xml:45
   Variable 'myVar' is defined but never used in <OnCreate>
```

**Unreachable Code**:
```
⚠ MyMod.xml:67
   Unreachable code in <OnUpdate>: if condition is always false (Nil/false)
```

**Expensive Operations**:
```
⚠ MyMod.xml:89
   Expensive operation 'sysFindObject' in frequently-called event <OnUpdate>: 
   Expensive - searches all objects in system
```

**Deprecated Functions**:
```
❌ MyMod.xml:120
   Deprecated function 'objDestroy' in <OnCreate>: 
   API 57 requires source parameter. Consider: objDestroy obj objSource
```

### 🎨 UI Features

- **TML Analysis Button**: New button in Semantic Validation tab
- **Filter Dropdown**: Filter by issue type
- **Color Coding**: Red for errors, yellow for warnings
- **Detailed Grid**: Shows file, line, severity, code, message
- **Double-click**: Jump to code location

### 🔍 Technical Details

- **Variable Tracking**: Parses block and setq definitions
- **Usage Analysis**: Tracks variable references
- **Control Flow**: Analyzes if conditions
- **Event Detection**: Identifies frequently-called events
- **Function Database**: 10+ deprecated functions tracked

### 💡 Benefits

- **Find Dead Code**: Detect unused variables and unreachable code
- **Performance**: Avoid expensive operations in hot paths
- **API Compliance**: Flag deprecated functions
- **Code Quality**: Improve mod code quality
- **Modern Tooling**: Feel like using a modern engine

---

## Version 4.4 - Resource Integrity Checker

### 🎯 Major New Feature

#### 1. Comprehensive Resource Validation 🧰
- ✅ Validate image sizes match declared dimensions
- ✅ Check spritesheets have correct frame counts
- ✅ Verify sound files exist and are valid formats
- ✅ Detect missing /Resources entries
- ✅ Check image dimensions and frame calculations
- ✅ Validate spritesheet layout (columns/rows)

#### 2. Resource Integrity UI 📊
- ✅ New "Resource Integrity" button in Project Health tab
- ✅ Detailed report with severity levels
- ✅ Grouped by resource type (Image, Sound, Resource)
- ✅ Shows file, line, and resource path for each issue

#### 3. Validation Features 🔍

**Image Validation**:
- Checks if bitmap/bitmask files exist
- Validates declared width/height against actual image
- Verifies spritesheet frame counts
- Checks rotation column/row calculations
- Detects invalid image formats

**Sound Validation**:
- Checks if sound files exist
- Validates file format (.wav, .mp3, .ogg)
- Warns about unsupported formats

**Resource Entry Validation**:
- Detects missing /Resources entries
- Checks file references in paths
- Validates resource file existence

### 📊 What It Catches

**Image Issues**:
- ❌ Missing bitmap/bitmask files
- ❌ Image size mismatches (declared vs. actual)
- ❌ Spritesheet frame count errors
- ❌ Invalid spritesheet layouts
- ⚠ Invalid image formats

**Sound Issues**:
- ❌ Missing sound files
- ⚠ Unsupported sound formats

**Resource Issues**:
- ⚠ Missing /Resources entries
- ⚠ Referenced files not found

### 🎨 Report Format

```
═══════════════════════════════════════════════════════════
              RESOURCE INTEGRITY REPORT
═══════════════════════════════════════════════════════════

Files Scanned: 15
Issues Found: 8

Errors: 3
Warnings: 5

═══════════════════════════════════════════════════════════
Image Issues (5)
═══════════════════════════════════════════════════════════

❌ MyMod.xml:45
   Image width mismatch: declared 128, actual 256
   Resource: Resources/ship.jpg

⚠ MyMod.xml:67
   Image bitmask file not found: Resources/ship_mask.bmp
   Resource: Resources/ship_mask.bmp
```

### 🔍 Technical Details

- **Image Reading**: Uses .NET System.Drawing.Image
- **Path Resolution**: Tries file directory, then mod root
- **Format Validation**: Checks file extensions and formats
- **Dimension Checking**: Compares declared vs. actual sizes
- **Spritesheet Math**: Validates frame count calculations

### 💡 Benefits

- **Catch Runtime Errors Early**: Find issues before game loads
- **Validate Dimensions**: Ensure images match declared sizes
- **Check Spritesheets**: Verify frame counts are correct
- **Find Missing Files**: Detect missing resources instantly
- **Format Validation**: Ensure supported file formats

---

## Version 4.3 - Enhanced UNID Intelligence

### 🎯 Major Enhancements

#### 1. UNID Reference Tracking 🧭
- ✅ Show where each UNID is referenced
- ✅ Reference count for each UNID
- ✅ Line numbers and context for each reference
- ✅ Double-click to view all references

#### 2. Dangling UNID Detection ⚠️
- ✅ Detect UNIDs that nothing uses
- ✅ Separate tab for dangling UNIDs
- ✅ Helps identify dead code
- ✅ Color-coded warnings

#### 3. Override Conflict Detection 🔥
- ✅ Detect UNIDs overridden by multiple mods
- ✅ Shows which mods conflict
- ✅ Critical for modpack compatibility
- ✅ Separate tab for conflicts

#### 4. Unused UNID Range Suggestions 💡
- ✅ Suggest unused UNID ranges for new mods
- ✅ Finds gaps in user UNID space (0xD000-0xEFFF)
- ✅ Respects reserved ranges
- ✅ Shows range size and availability

### 📊 Intelligence Report Features

**Four Tabs**:
1. **All UNIDs**: Complete list with reference counts
2. **Dangling UNIDs**: UNIDs that nothing references
3. **Override Conflicts**: UNIDs defined in multiple mods
4. **Unused Ranges**: Available UNID ranges for new mods

**Reference Details**:
- File and line number for each reference
- Context line showing where UNID is used
- Reference count summary
- Double-click to view all references

### 🔍 What It Detects

**Dangling UNIDs**:
- UNIDs defined but never referenced
- Potential dead code
- Unused entity definitions

**Override Conflicts**:
- Same UNID defined in multiple mods
- Will cause conflicts in modpacks
- Critical for compatibility

**Unused Ranges**:
- Gaps in user UNID space
- Safe ranges for new mods
- Respects reserved ranges

### 🎨 UI Features

- **Intelligence Button**: New button in UNID Manager
- **Tabbed Interface**: Four tabs for different views
- **Color Coding**: Warnings for dangling/conflicts
- **Reference Viewer**: Double-click to see all references
- **Range Suggestions**: Available UNID ranges

---

## Version 4.2 - Event Flow Analyzer

### 🎯 Major New Feature

#### 1. Comprehensive Event Flow Analysis 🔗
- ✅ Show all events a type implements
- ✅ Show all events it inherits
- ✅ Identify events never called by engine
- ✅ Detect duplicate event handlers
- ✅ Detect unreachable event handlers
- ✅ Event status tracking (called vs. not called)

#### 2. Event Flow UI 📊
- ✅ New "Event Flow" button in Semantic Validation tab
- ✅ Filter by event type (Implemented, Inherited, Duplicate, Unused)
- ✅ Filter by type name
- ✅ Color-coded status indicators
- ✅ Detailed event information

#### 3. Known Events Database 🧠
- ✅ Comprehensive list of Transcendence events
- ✅ Tracks which events are called by engine
- ✅ Event descriptions
- ✅ Type-specific event information

### 📊 What It Shows

**Event Flow Report**:
```
Type: MyShip
Total Events: 8
Implemented: 5
Inherited: 3
Duplicate: 0
Unused: 1

Implemented Events:
  OnCreate (Line 45) ✓ Called by engine
  OnUpdate (Line 67) ✓ Called by engine
  OnDamage (Line 89) ✓ Called by engine
  CustomEvent (Line 120) ⚠ May not be called

Inherited Events:
  OnDestroy (from BaseShip)
  OnFireWeapon (from BaseShip)

Unused Events:
  CustomEvent ⚠ Unknown event - likely custom
```

### 🔍 Detection Features

**Detects**:
- ✅ Events implemented by type
- ✅ Events inherited from parent
- ✅ Duplicate event handlers (same event defined multiple times)
- ✅ Events that may not be called by engine
- ✅ Custom events vs. known engine events

**Status Indicators**:
- ✓ Called by engine - Event is known and called
- ⚠ May not be called - Custom or unknown event
- ⚠ Duplicate handler - Event defined multiple times

### 🎨 UI Features

- **Filter Dropdown**: Filter by event type
- **Type Selector**: Filter by specific type
- **Color Coding**: Green for called, yellow for warnings
- **Detailed Grid**: Shows type, event, status, line, details
- **Double-click**: Jump to event handler in code

---

## Version 4.1 - Enhanced Inheritance & Override Resolution

### 🎯 Major Enhancements

#### 1. Fully Resolved Types 🧬
- ✅ Expand inherited types into fully resolved "final" version
- ✅ Shows all attributes with their sources (parent vs. self)
- ✅ Merges attributes from inheritance chain
- ✅ Displays inheritance chain visually

#### 2. Override Conflict Detection ⚠️
- ✅ Detects when child overrides parent attributes
- ✅ Warns about immutable attribute overrides
- ✅ Shows old vs. new values for overrides
- ✅ Identifies potential breaking changes

#### 3. Attribute Source Tracking 📊
- ✅ Shows which attributes come from parent types
- ✅ Shows which attributes are defined in child
- ✅ Tracks attribute origins through inheritance chain
- ✅ Visual distinction between inherited and overridden

#### 4. Enhanced Inheritance Tree Viewer 🧭
- ✅ Type selector dropdown
- ✅ Live resolved type view
- ✅ Full attribute listing with sources
- ✅ Event handler listing with sources
- ✅ Conflict highlighting

### 📊 What It Shows

**Fully Resolved Type Display**:
```
Type: MyShip (ShipClass)
UNID: 0xE1271001
File: MyMod.xml

Inheritance Chain:
  MyShip → BaseShip → StandardShip

Attributes:
name = "My Ship"
  Source: Self: MyShip
level = "5"
  Source: Parent: BaseShip
mass = "100"
  Source: Self: MyShip

Override Conflicts:
⚠ Attribute: level
  Parent value: 3
  Child value:  5
  Source: Parent: BaseShip
```

### 🔍 Conflict Detection

**Detects**:
- Attribute value changes from parent
- Immutable attribute overrides (error)
- Breaking parent assumptions
- Override conflicts

**Example Warnings**:
```
Error: Type 'MyShip' overrides immutable attribute 'immutable' from parent
Warning: Type 'MyShip' overrides attribute 'level' from parent (was: '3', now: '5')
```

### 🎨 UI Improvements

- **Type Selector**: Dropdown to choose any type
- **Live View**: Updates when type is selected
- **Color Coding**: Conflicts highlighted
- **Source Tracking**: Clear indication of attribute origins

---

## Version 4.0 - Source-Aware Semantic Validation

### 🎯 Major New Features

#### 1. Semantic Validation (Beyond Syntax) 🌐
- ✅ New "Semantic Validation" tab
- ✅ Detects missing ArmorClass references in ShipClass/StationType
- ✅ Validates Device references
- ✅ Validates Weapon type references
- ✅ Checks inherit references
- ✅ Type registry building
- ✅ Cross-file reference validation

#### 2. Inheritance & Override Resolution 🧬
- ✅ Inheritance tree visualization
- ✅ Parent-child relationship tracking
- ✅ Inherit chain resolution
- ✅ Override conflict detection (preparation)

#### 3. Event Flow Analyzer 🔗
- ✅ Event handler detection
- ✅ Event usage mapping
- ✅ Type-to-events relationship tracking

### 📊 Semantic Validation Features
- **Type Registry**: Builds complete registry of all types across files
- **Reference Validation**: Checks all type references are valid
- **Missing Type Detection**: Finds references to nonexistent types
- **Inheritance Tracking**: Maps inheritance relationships
- **Event Mapping**: Tracks which types implement which events

### 🔍 What It Catches
- ShipClass referencing nonexistent ArmorClass
- StationType referencing nonexistent armor
- Device references to missing ItemTypes
- Weapon references to missing weapon types
- Inherit references to missing parent types

### 📈 Architecture
- New module: `TranscendenceModTools_Semantic.ps1` (~15KB)
- Integrated into main GUI
- Two-pass analysis (registry building, then validation)
- Color-coded severity display

---

## Version 3.2 - Dependency Graph & Enhanced Formatting

### 🎯 New Features

#### 1. Dependency Graph Visualization 🧭
- ✅ New "Dependency Graph" tab
- ✅ Visualizes relationships between mod elements:
  - Items → Weapons
  - Ships → Items/Weapons
  - Stations → Encounters
  - Stations → Ships
  - Items → Events
- ✅ Grouped by relationship type
- ✅ Export functionality
- ✅ Comprehensive dependency analysis

#### 2. Enhanced XML Formatting 🧬
- ✅ Improved formatting to match Transcendence 2.0.7 style
- ✅ Better attribute alignment
- ✅ Proper tab-based indentation
- ✅ Handles complex XML structures
- ✅ Fallback formatting for malformed XML

### 📊 Dependency Graph Features
- Tracks all UNID relationships
- Shows which items use which weapons
- Shows which ships carry which items
- Shows which stations spawn which encounters
- Shows event handler relationships
- Export to text file

---

## Version 3.1 - Enhanced Health Report

### 🎯 Enhanced Mod Health Report
- ✅ Detailed statistics display
- ✅ XML errors count
- ✅ Missing resources count
- ✅ Unused UNIDs detection and count
- ✅ Deprecated attributes detection and count
- ✅ Inconsistent indentation detection and count
- ✅ Color-coded status indicators (✓, ⚠, ❌)
- ✅ Formatted summary in requested format

### 🔍 New Detection Functions
- ✅ `Get-DeprecatedAttributeIssues` - Detects old API versions
- ✅ `Get-IndentationIssues` - Detects mixed tabs/spaces
- ✅ `Get-UnusedUnids` - Finds UNIDs defined but never referenced

### 📊 Report Format
The health report now shows:
```
✓ XML errors:                    0
⚠ Missing resources:             3
⚠ Unused UNIDs:                   2
⚠ Deprecated attributes:          1
⚠ Files with inconsistent indentation: 4
```

---

## Version 3.0 - Complete Feature Set

### 🎉 Major New Features

#### 1. XML Auto-Formatting
- ✅ Normalize indentation (tabs)
- ✅ Align attributes
- ✅ Break long lines
- ✅ Consistent formatting
- ✅ Format button in XML Checker tab

#### 2. UNID Manager Tab
- ✅ Scan and list all UNIDs in mod
- ✅ Detect duplicates
- ✅ Generate new UNIDs
- ✅ View UNID by type (Item, Ship, Station, etc.)
- ✅ Color-coded duplicates

#### 3. Cross-Mod Compatibility Checker
- ✅ Scan all mods in Extensions folder
- ✅ Detect UNID conflicts between mods
- ✅ Show which mods conflict
- ✅ Comprehensive conflict report

### 📦 New Modules
- ✅ `TranscendenceModTools_Formatting.ps1` - XML formatting engine

### 🎨 UI Improvements
- ✅ Expanded form width for new tabs
- ✅ 5 tabs total: XML Checker, Error Helper, Project Health, UNID Manager, Cross-Mod Check
- ✅ Better button layout

---

## Version 2.1 - Polish & Resource Validation

### 🎨 UI Improvements
- ✅ Menu bar with File and Help menus
- ✅ Export functionality (CSV and TXT formats)
- ✅ About dialog with version info
- ✅ Quick Reference launcher from Help menu
- ✅ Better error handling throughout

### 🔍 New Features
- ✅ Resource Path Validator
  - Checks if referenced image files exist
  - Checks if referenced sound files exist
  - Warns about missing resources
  - Handles relative and absolute paths

### 📦 Export Features
- ✅ Export issues to CSV
- ✅ Export issues to TXT
- ✅ Includes all issue details
- ✅ Timestamped reports

---

## Version 2.0 - Advanced Features Release

### 🎉 Major New Features

#### 1. XML Structure Validator
- ✅ Unclosed tag detection
- ✅ Tag mismatch detection  
- ✅ Duplicate attribute detection
- ✅ Unexpected closing tag detection
- ✅ Line and column precision

#### 2. TLisp Expression Checker
- ✅ Parentheses balance checking
- ✅ Unbalanced `(` and `)` detection
- ✅ Extra closing parenthesis detection
- ✅ Suspicious `(@ var)` construct detection
- ✅ Works in all TLisp blocks (`<Events>`, `<OnCreate>`, `<Globals>`, etc.)

#### 3. UNID Reference Checker
- ✅ Duplicate UNID detection across files
- ✅ Missing entity reference detection
- ✅ Invalid UNID format warnings
- ✅ Entity definition tracking
- ✅ Cross-file UNID collision detection

#### 4. Project Health Report (New Tab)
- ✅ Comprehensive project summary
- ✅ Files with errors/warnings count
- ✅ Total issues breakdown
- ✅ UNID duplicate count
- ✅ Per-file status display
- ✅ Visual indicators (✓, ⚠, ❌)

#### 5. Enhanced Documentation
- ✅ Expanded element documentation database
- ✅ Attribute information
- ✅ Example usage
- ✅ Quick reference guide

### 🔧 Improvements

- ✅ Better error handling with try-catch blocks
- ✅ Graceful degradation if advanced module fails to load
- ✅ Per-function error handling in advanced checks
- ✅ Improved status messages
- ✅ Enhanced Project Health report formatting

### 📚 Documentation

- ✅ `FEATURES.md` - Complete feature list
- ✅ `QUICK_REFERENCE.md` - Quick start guide
- ✅ `CHANGELOG.md` - This file
- ✅ Updated `README_Checker.txt`

### 🐛 Bug Fixes

- ✅ Fixed advanced module loading
- ✅ Fixed function reference passing
- ✅ Improved error messages
- ✅ Better file path handling

### 📦 File Structure

```
Tools/
├── TranscendenceModTools.ps1          (Main tool - GUI)
├── TranscendenceModTools_Advanced.ps1 (Advanced features module)
├── TranscendenceModTools.bat          (Launcher)
├── README_Checker.txt                  (User guide)
├── FEATURES.md                        (Feature documentation)
├── QUICK_REFERENCE.md                 (Quick start)
└── CHANGELOG.md                       (This file)
```

### 🎯 Usage

1. **Basic Scanning**: XML Checker tab → Enter path → Scan
2. **Error Diagnosis**: Error Helper tab → Paste error → Analyze
3. **Project Health**: Project Health tab → Enter folder → Generate Report

### 🚀 What's Next

Future enhancements planned:
- Syntax highlighting
- Real-time validation
- Resource preview
- Cross-mod compatibility checking
- Auto-formatting
- UNID management UI
- Dependency graph visualization

---

## Version 1.0 - Initial Release

### Core Features
- XML well-formedness checking
- BOM detection
- Raw `>` in content detection
- Invalid TLisp symbol syntax
- Error message parsing
- Auto-fix capabilities
- VS Code integration

