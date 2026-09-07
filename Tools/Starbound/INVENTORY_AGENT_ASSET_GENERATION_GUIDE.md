# InventoryAgent System Asset Generation Guide

Generate visual assets for the InventoryAgent System including UI panels, buttons, slot icons, container sprites, quick access elements, equipment presets, sorting/filtering elements, weight/volume indicators, transfer indicators, stack indicators, tooltip elements, and search UI elements.

## Quick Start

```powershell
# Generate all InventoryAgent assets
.\GenerateInventoryAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateInventoryAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Inventory UI Panels (5 panels)

1. **panel_inventory** - Inventory panel background
2. **panel_container** - Container panel background
3. **panel_quick_access** - Quick access panel background
4. **panel_equipment** - Equipment panel background
5. **panel_tooltip** - Tooltip panel background

### Inventory UI Buttons (8 buttons)

1. **button_sort** - Sort button
2. **button_filter** - Filter button
3. **button_stack** - Stack button
4. **button_transfer** - Transfer button
5. **button_search** - Search button
6. **button_close** - Close button
7. **button_save_preset** - Save preset button
8. **button_load_preset** - Load preset button

### Slot Icons (6 icons)

1. **slot_empty** - Empty slot
2. **slot_occupied** - Occupied slot
3. **slot_locked** - Locked slot
4. **slot_highlighted** - Highlighted slot
5. **slot_selected** - Selected slot
6. **slot_stackable** - Stackable slot

### Container Sprites (6 containers)

1. **container_bag** - Bag container
2. **container_chest** - Chest container
3. **container_backpack** - Backpack container
4. **container_pouch** - Pouch container
5. **container_shared** - Shared container
6. **container_equipment** - Equipment container

### Quick Access Bar Elements (3 elements)

1. **quick_access_slot** - Quick access slot
2. **quick_access_active** - Active quick access indicator
3. **quick_access_bar** - Quick access bar background

### Equipment Preset Icons (6 icons)

1. **preset_combat** - Combat preset
2. **preset_exploration** - Exploration preset
3. **preset_crafting** - Crafting preset
4. **preset_custom** - Custom preset
5. **preset_save** - Save preset
6. **preset_load** - Load preset

### Sorting/Filtering UI Elements (9 elements)

1. **sort_name** - Sort by name
2. **sort_value** - Sort by value
3. **sort_weight** - Sort by weight
4. **sort_category** - Sort by category
5. **sort_rarity** - Sort by rarity
6. **filter_category** - Category filter
7. **filter_rarity** - Rarity filter
8. **filter_tag** - Tag filter
9. **filter_clear** - Clear filter

### Weight/Volume Indicators (7 indicators)

1. **indicator_weight** - Weight indicator
2. **indicator_volume** - Volume indicator
3. **indicator_weight_low** - Low weight
4. **indicator_weight_medium** - Medium weight
5. **indicator_weight_high** - High weight
6. **indicator_weight_full** - Weight full
7. **indicator_volume_full** - Volume full

### Transfer Indicators (5 indicators)

1. **transfer_arrow** - Transfer arrow
2. **transfer_success** - Transfer success
3. **transfer_failed** - Transfer failed
4. **transfer_in_progress** - Transfer in progress
5. **transfer_all** - Transfer all

### Stack Indicators (4 indicators)

1. **stack_indicator** - Stack indicator
2. **stack_full** - Stack full
3. **stack_partial** - Stack partial
4. **stack_auto** - Auto stack

### Tooltip Elements (7 elements)

1. **tooltip_background** - Tooltip background
2. **tooltip_border** - Tooltip border
3. **tooltip_arrow** - Tooltip arrow
4. **tooltip_icon_stats** - Stats icon
5. **tooltip_icon_description** - Description icon
6. **tooltip_icon_requirements** - Requirements icon
7. **tooltip_icon_effects** - Effects icon

### Search UI Elements (4 elements)

1. **search_box** - Search box background
2. **search_icon** - Search icon
3. **search_clear** - Clear search
4. **search_results** - Search results indicator

## Total: ~70 Assets

## Output Structure

```
assets/
└── inventory/
    ├── ui/
    │   ├── panels/
    │   │   ├── panel_inventory.png
    │   │   ├── panel_container.png
    │   │   └── ... (all UI panels)
    │   └── buttons/
    │       ├── button_sort.png
    │       ├── button_filter.png
    │       └── ... (all UI buttons)
    ├── slots/
    │   ├── slot_empty.png
    │   ├── slot_occupied.png
    │   └── ... (all slot icons)
    ├── containers/
    │   ├── container_bag.png
    │   ├── container_chest.png
    │   └── ... (all container sprites)
    ├── quick_access/
    │   ├── quick_access_slot.png
    │   ├── quick_access_active.png
    │   └── ... (all quick access elements)
    ├── presets/
    │   ├── preset_combat.png
    │   ├── preset_exploration.png
    │   └── ... (all preset icons)
    ├── sort_filter/
    │   ├── sort_name.png
    │   ├── sort_value.png
    │   └── ... (all sort/filter elements)
    ├── weight_volume/
    │   ├── indicator_weight.png
    │   ├── indicator_volume.png
    │   └── ... (all weight/volume indicators)
    ├── transfer/
    │   ├── transfer_arrow.png
    │   ├── transfer_success.png
    │   └── ... (all transfer indicators)
    ├── stack/
    │   ├── stack_indicator.png
    │   ├── stack_full.png
    │   └── ... (all stack indicators)
    ├── tooltips/
    │   ├── tooltip_background.png
    │   ├── tooltip_border.png
    │   └── ... (all tooltip elements)
    └── search/
        ├── search_box.png
        ├── search_icon.png
        └── ... (all search elements)
```

## Integration

### InventoryAgent

```cpp
// Create container
InventoryAgent::createContainer(capacity, name);
// Uses: /assets/inventory/containers/container_*.png
// Uses: /assets/inventory/ui/panels/panel_container.png

// Add item to container
InventoryAgent::addItemToContainer(containerId, item);
// Uses: /assets/inventory/slots/slot_occupied.png
// Uses: /assets/inventory/stack/stack_indicator.png

// Transfer between containers
InventoryAgent::transferBetweenContainers(fromId, toId, itemId, count);
// Uses: /assets/inventory/transfer/transfer_arrow.png
// Uses: /assets/inventory/transfer/transfer_success.png

// Stack container
InventoryAgent::stackContainer(containerId);
// Uses: /assets/inventory/ui/buttons/button_stack.png
// Uses: /assets/inventory/stack/stack_auto.png

// Sort container
InventoryAgent::sortContainer(container, SortKey::Name, true);
// Uses: /assets/inventory/ui/buttons/button_sort.png
// Uses: /assets/inventory/sort_filter/sort_name.png

// Filter items
InventoryAgent::filterItems(container);
// Uses: /assets/inventory/ui/buttons/button_filter.png
// Uses: /assets/inventory/sort_filter/filter_*.png

// Set quick access item
InventoryAgent::setQuickAccessItem(itemId, slotIndex);
// Uses: /assets/inventory/quick_access/quick_access_slot.png
// Uses: /assets/inventory/quick_access/quick_access_active.png

// Save preset
InventoryAgent::savePreset(name, equipment);
// Uses: /assets/inventory/ui/buttons/button_save_preset.png
// Uses: /assets/inventory/presets/preset_*.png

// Load preset
InventoryAgent::loadPreset(name);
// Uses: /assets/inventory/ui/buttons/button_load_preset.png
// Uses: /assets/inventory/presets/preset_*.png

// Generate tooltip
InventoryAgent::generateTooltip(item);
// Uses: /assets/inventory/tooltips/tooltip_background.png
// Uses: /assets/inventory/tooltips/tooltip_border.png
// Uses: /assets/inventory/tooltips/tooltip_icon_*.png

// Search items
InventoryAgent::searchItems(query);
// Uses: /assets/inventory/ui/buttons/button_search.png
// Uses: /assets/inventory/search/search_box.png
// Uses: /assets/inventory/search/search_icon.png
```

### Container

```cpp
// Add item
Container::addItem(item);
// Uses: /assets/inventory/slots/slot_empty.png
// Uses: /assets/inventory/slots/slot_occupied.png
// Uses: /assets/inventory/stack/stack_indicator.png

// Calculate total weight
Container::totalWeight();
// Uses: /assets/inventory/weight_volume/indicator_weight.png

// Auto stack
Container::autoStack();
// Uses: /assets/inventory/stack/stack_auto.png

// Sort
Container::sortByName(true);
// Uses: /assets/inventory/sort_filter/sort_name.png
```

## Container Types

### Container Variants
- **Bag**: Basic inventory bag
- **Chest**: Storage chest
- **Backpack**: Backpack container
- **Pouch**: Item pouch
- **Shared**: Shared storage container
- **Equipment**: Equipment storage container

## Slot States

### Slot Types
- **Empty**: Empty slot
- **Occupied**: Slot with item
- **Locked**: Locked slot
- **Highlighted**: Highlighted slot
- **Selected**: Selected slot
- **Stackable**: Stackable slot

## Quick Access System

### Quick Access Features
- Quick access slots for fast item access
- Active slot indicator
- Quick access bar background

## Equipment Presets

### Preset Types
- **Combat**: Combat equipment preset
- **Exploration**: Exploration equipment preset
- **Crafting**: Crafting equipment preset
- **Custom**: Custom equipment preset

## Sorting System

### Sort Keys
- **Name**: Sort by item name
- **Value**: Sort by item value
- **Weight**: Sort by item weight
- **Category**: Sort by item category
- **Rarity**: Sort by item rarity

## Filtering System

### Filter Types
- **Category**: Filter by category
- **Rarity**: Filter by rarity
- **Tag**: Filter by tag
- **Clear**: Clear all filters

## Weight/Volume Management

### Weight States
- **Low**: Low weight
- **Medium**: Medium weight
- **High**: High weight
- **Full**: Weight limit reached

### Volume States
- **Full**: Volume limit reached

## Transfer System

### Transfer States
- **Arrow**: Transfer direction indicator
- **Success**: Transfer successful
- **Failed**: Transfer failed
- **In Progress**: Transfer in progress
- **All**: Transfer all items

## Stack System

### Stack States
- **Indicator**: Stack indicator
- **Full**: Stack at maximum
- **Partial**: Partial stack
- **Auto**: Auto stacking enabled

## Tooltip System

### Tooltip Components
- **Background**: Tooltip background
- **Border**: Tooltip border
- **Arrow**: Tooltip pointer
- **Stats Icon**: Item statistics icon
- **Description Icon**: Item description icon
- **Requirements Icon**: Item requirements icon
- **Effects Icon**: Item effects icon

## Search System

### Search Components
- **Search Box**: Search input background
- **Search Icon**: Search icon
- **Clear Search**: Clear search button
- **Search Results**: Search results indicator

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateInventoryAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure InventoryAgent

Set up InventoryAgent with asset paths.

### Step 3: Create Container

```cpp
InventoryAgent agent;
auto container = agent.createContainer(100, "My Container");
```

### Step 4: Add Items

```cpp
Item item;
item.id = "my_item";
agent.addItemToContainer("My Container", item);
```

### Step 5: Use Inventory UI

```cpp
// Sort items
agent.sortContainer(*container, SortKey::Name, true);

// Filter items
agent.setActiveFilters({"weapon", "rare"});

// Stack items
agent.stackContainer("My Container");
```

### Step 6: Test in Game

Load the mod and test inventory system in-game.

## Advanced Options

### Custom Container Types

Edit `GenerateInventoryAgentAssets.ps1` to add custom container types.

### Custom UI Elements

Add custom UI elements as needed.

### Custom Presets

Add custom equipment presets with unique icons.

## Tips

1. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
2. **UI buttons**: Use 32x32 for buttons
3. **Slot icons**: Use 32x32 for slot icons
4. **Container sprites**: Use 32x32 for container sprites
5. **Stack indicators**: Use 16x16 for small stack indicators
6. **Tooltip elements**: Keep tooltips simple and clear
7. **Search elements**: Make search UI intuitive

## Troubleshooting

### Inventory Not Displaying

- Check UI panel paths
- Verify panels are in `assets/inventory/ui/panels/`
- Ensure InventoryAgent is initialized

### Slots Not Showing

- Check slot icon paths
- Verify icons are in `assets/inventory/slots/`
- Ensure slot system is configured

### Containers Not Working

- Check container sprite paths
- Verify sprites are in `assets/inventory/containers/`
- Ensure container system is initialized

### Transfer Not Functioning

- Check transfer indicator paths
- Verify indicators are in `assets/inventory/transfer/`
- Ensure transfer system is enabled

### Stacking Not Working

- Check stack indicator paths
- Verify indicators are in `assets/inventory/stack/`
- Ensure stacking system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
