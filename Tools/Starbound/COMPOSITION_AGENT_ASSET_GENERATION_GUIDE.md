# CompositionAgent System Asset Generation Guide

Generate visual assets for the CompositionAgent System including node type icons, shape type icons, effect type icons, modifier type icons, tree visualization elements, composition UI elements, template icons, metrics display elements, simulation preview elements, validation indicators, cache indicators, and performance monitoring UI elements.

## Quick Start

```powershell
# Generate all CompositionAgent assets
.\GenerateCompositionAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateCompositionAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Node Type Icons (8 icons)

1. **node_shape** - Shape node icon
2. **node_effect** - Effect node icon
3. **node_modifier** - Modifier node icon
4. **node_control** - Control node icon
5. **node_trigger** - Trigger node icon
6. **node_vfx** - VFX node icon
7. **node_sfx** - SFX node icon
8. **node_chance_trigger** - Chance trigger node icon

### Shape Type Icons (4 icons)

1. **shape_projectile** - Projectile shape icon
2. **shape_beam** - Beam shape icon
3. **shape_aoe** - AOE shape icon
4. **shape_root** - Root shape icon

### Effect Type Icons (5 icons)

1. **effect_damage_fire** - Fire damage effect icon
2. **effect_heal** - Heal effect icon
3. **effect_status_freeze** - Freeze status effect icon
4. **effect_damage_ice** - Ice damage effect icon
5. **effect_damage_lightning** - Lightning damage effect icon

### Modifier Type Icons (3 icons)

1. **modifier_bounce** - Bounce modifier icon
2. **modifier_chain** - Chain modifier icon
3. **modifier_repeat** - Repeat modifier icon

### Tree Visualization Elements (7 elements)

1. **tree_connection** - Tree connection line
2. **tree_branch** - Tree branch line
3. **tree_node_background** - Node background
4. **tree_root** - Tree root indicator
5. **tree_leaf** - Tree leaf indicator
6. **tree_collapsed** - Collapsed node indicator
7. **tree_expanded** - Expanded node indicator

### Composition UI Elements (15 elements)

1. **ui_panel_composition** - Composition editor panel
2. **ui_panel_tree_view** - Tree view panel
3. **ui_panel_metrics** - Metrics panel
4. **ui_panel_simulation** - Simulation panel
5. **ui_button_create_node** - Create node button
6. **ui_button_delete_node** - Delete node button
7. **ui_button_connect** - Connect nodes button
8. **ui_button_disconnect** - Disconnect nodes button
9. **ui_button_validate** - Validate tree button
10. **ui_button_optimize** - Optimize tree button
11. **ui_button_simulate** - Simulate button
12. **ui_button_save_template** - Save template button
13. **ui_button_load_template** - Load template button
14. **ui_button_export** - Export button
15. **ui_button_import** - Import button

### Template Icons (5 icons)

1. **template_basic** - Basic template icon
2. **template_advanced** - Advanced template icon
3. **template_custom** - Custom template icon
4. **template_save** - Save template icon
5. **template_load** - Load template icon

### Metrics Display Elements (7 elements)

1. **metrics_mana_cost** - Mana cost indicator
2. **metrics_cooldown** - Cooldown indicator
3. **metrics_damage** - Damage indicator
4. **metrics_area** - Area indicator
5. **metrics_cc_time** - Crowd control time indicator
6. **metrics_heal** - Heal indicator
7. **metrics_targets** - Targets hit indicator

### Simulation Preview Elements (5 elements)

1. **simulation_play** - Play simulation button
2. **simulation_pause** - Pause simulation button
3. **simulation_stop** - Stop simulation button
4. **simulation_reset** - Reset simulation button
5. **simulation_preview** - Simulation preview background

### Validation Indicators (5 indicators)

1. **validation_valid** - Valid indicator
2. **validation_invalid** - Invalid indicator
3. **validation_warning** - Warning indicator
4. **validation_error** - Error indicator
5. **validation_circular** - Circular reference indicator

### Cache Indicators (5 indicators)

1. **cache_metrics** - Metrics cache indicator
2. **cache_simulation** - Simulation cache indicator
3. **cache_hit** - Cache hit indicator
4. **cache_miss** - Cache miss indicator
5. **cache_clear** - Clear cache button

### Performance Monitoring UI Elements (5 elements)

1. **performance_memory** - Memory usage indicator
2. **performance_cpu** - CPU usage indicator
3. **performance_processing_time** - Processing time indicator
4. **performance_cache_hit_rate** - Cache hit rate indicator
5. **performance_stats** - Performance stats panel

## Total: ~75 Assets

## Output Structure

```
assets/
└── composition/
    ├── nodes/
    │   ├── node_shape.png
    │   ├── node_effect.png
    │   └── ... (all node type icons)
    ├── shapes/
    │   ├── shape_projectile.png
    │   ├── shape_beam.png
    │   └── ... (all shape type icons)
    ├── effects/
    │   ├── effect_damage_fire.png
    │   ├── effect_heal.png
    │   └── ... (all effect type icons)
    ├── modifiers/
    │   ├── modifier_bounce.png
    │   ├── modifier_chain.png
    │   └── ... (all modifier type icons)
    ├── tree/
    │   ├── tree_connection.png
    │   ├── tree_branch.png
    │   └── ... (all tree visualization elements)
    ├── ui/
    │   ├── ui_panel_composition.png
    │   ├── ui_button_create_node.png
    │   └── ... (all composition UI elements)
    ├── templates/
    │   ├── template_basic.png
    │   ├── template_advanced.png
    │   └── ... (all template icons)
    ├── metrics/
    │   ├── metrics_mana_cost.png
    │   ├── metrics_cooldown.png
    │   └── ... (all metrics display elements)
    ├── simulation/
    │   ├── simulation_play.png
    │   ├── simulation_pause.png
    │   └── ... (all simulation preview elements)
    ├── validation/
    │   ├── validation_valid.png
    │   ├── validation_invalid.png
    │   └── ... (all validation indicators)
    ├── cache/
    │   ├── cache_metrics.png
    │   ├── cache_simulation.png
    │   └── ... (all cache indicators)
    └── performance/
        ├── performance_memory.png
        ├── performance_cpu.png
        └── ... (all performance monitoring elements)
```

## Integration

### CompositionAgent

```cpp
// Create node
CompositionAgent::createNode("Shape", nodeId);
// Uses: /assets/composition/nodes/node_shape.png

// Create tree
CompositionAgent::createTree(treeId);
// Uses: /assets/composition/tree/tree_root.png
// Uses: /assets/composition/tree/tree_connection.png
// Uses: /assets/composition/tree/tree_node_background.png

// Calculate metrics
CompositionAgent::calculateMetrics(nodeId);
// Uses: /assets/composition/metrics/metrics_*.png

// Simulate node
CompositionAgent::simulateNode(nodeId, context);
// Uses: /assets/composition/simulation/simulation_*.png

// Validate tree
CompositionAgent::validateTree(treeId);
// Uses: /assets/composition/validation/validation_*.png

// Save template
CompositionAgent::saveAsTemplate(treeId, templateId);
// Uses: /assets/composition/templates/template_save.png

// Load template
CompositionAgent::createFromTemplate(templateId);
// Uses: /assets/composition/templates/template_load.png
```

### SpellNode Types

```cpp
// ShapeNode
ShapeNode node;
node.shapeType = "projectile";
// Uses: /assets/composition/shapes/shape_projectile.png

// EffectNode
EffectNode node;
node.effectType = "damage.fire";
// Uses: /assets/composition/effects/effect_damage_fire.png

// ModifierNode
ModifierNode node;
node.modifierType = "bounce";
// Uses: /assets/composition/modifiers/modifier_bounce.png
```

## Node Types

### ShapeNode
- **projectile**: Projectile spell shape
- **beam**: Beam spell shape
- **aoe**: Area of effect spell shape
- **root**: Root spell shape

### EffectNode
- **damage.fire**: Fire damage effect
- **damage.ice**: Ice damage effect
- **damage.lightning**: Lightning damage effect
- **heal**: Healing effect
- **status.freeze**: Freeze status effect

### ModifierNode
- **bounce**: Bounce modifier
- **chain**: Chain modifier
- **repeat**: Repeat modifier

### ControlNode
- **delay**: Delay control
- **conditional**: Conditional control

### TriggerNode
- **onImpact**: On impact trigger
- **onExpire**: On expire trigger

### VFXNode
- Visual effects node

### SFXNode
- Sound effects node

### ChanceTriggerNode
- Probabilistic trigger node

## Tree Visualization

### Tree Structure
- **Root**: Root node of the tree
- **Branches**: Connection lines between nodes
- **Leaves**: Leaf nodes (nodes with no children)
- **Connections**: Visual connections between parent and child nodes

### Tree States
- **Expanded**: Node with visible children
- **Collapsed**: Node with hidden children

## Composition UI

### Editor Panels
- **Composition Panel**: Main composition editor
- **Tree View Panel**: Tree structure visualization
- **Metrics Panel**: Spell metrics display
- **Simulation Panel**: Spell simulation preview

### Editor Buttons
- **Create Node**: Create new node
- **Delete Node**: Delete selected node
- **Connect**: Connect two nodes
- **Disconnect**: Disconnect nodes
- **Validate**: Validate tree structure
- **Optimize**: Optimize tree structure
- **Simulate**: Run spell simulation
- **Save Template**: Save tree as template
- **Load Template**: Load tree from template
- **Export**: Export tree to file
- **Import**: Import tree from file

## Metrics System

### SpellMetrics
- **manaCost**: Mana cost of the spell
- **cooldown**: Cooldown time
- **totalDamage**: Total damage output
- **areaCovered**: Area covered by the spell
- **crowdControlTime**: Crowd control duration
- **healAmount**: Healing amount
- **targetsHit**: Number of targets hit

## Simulation System

### Simulation Controls
- **Play**: Start simulation
- **Pause**: Pause simulation
- **Stop**: Stop simulation
- **Reset**: Reset simulation state

### Simulation Preview
- Visual preview of spell behavior
- Real-time spell effect visualization

## Validation System

### Validation States
- **Valid**: Tree is valid
- **Invalid**: Tree has validation errors
- **Warning**: Tree has warnings
- **Error**: Tree has critical errors
- **Circular Reference**: Circular reference detected

## Cache System

### Cache Types
- **Metrics Cache**: Cached spell metrics
- **Simulation Cache**: Cached simulation results

### Cache States
- **Hit**: Cache hit (data found in cache)
- **Miss**: Cache miss (data not in cache)
- **Clear**: Clear cache button

## Performance Monitoring

### Performance Metrics
- **Memory Usage**: Current memory usage
- **CPU Usage**: Current CPU usage
- **Processing Time**: Average processing time
- **Cache Hit Rate**: Cache hit rate percentage

### Performance Stats Panel
- Visual display of performance metrics
- Real-time performance monitoring

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateCompositionAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure CompositionAgent

Set up CompositionAgent with asset paths.

### Step 3: Create Node

```cpp
CompositionAgent agent;
auto node = agent.createNode("Shape", "my_node");
```

### Step 4: Create Tree

```cpp
auto tree = agent.createTree("my_tree");
agent.addChildToNode("my_tree", "my_node");
```

### Step 5: Calculate Metrics

```cpp
auto metrics = agent.calculateTreeMetrics("my_tree");
```

### Step 6: Simulate Spell

```cpp
SpellContext context;
agent.simulateTree("my_tree", context);
```

### Step 7: Validate Tree

```cpp
bool isValid = agent.validateTree("my_tree");
```

### Step 8: Test in Game

Load the mod and test composition system in-game.

## Advanced Options

### Custom Node Types

Edit `GenerateCompositionAgentAssets.ps1` to add custom node types.

### Custom Shape Types

Add custom shape types as needed.

### Custom Effect Types

Add custom effect types with unique icons.

## Tips

1. **Node icons**: Use 32x32 for node type icons
2. **Tree elements**: Keep tree visualization simple and clear
3. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
4. **UI buttons**: Use 32x32 for buttons
5. **Metrics icons**: Use 32x32 for metrics indicators
6. **Validation indicators**: Make validation states visually distinct
7. **Cache indicators**: Keep cache indicators simple

## Troubleshooting

### Nodes Not Displaying

- Check node icon paths
- Verify icons are in `assets/composition/nodes/`
- Ensure CompositionAgent is initialized

### Tree Not Rendering

- Check tree visualization element paths
- Verify elements are in `assets/composition/tree/`
- Ensure tree structure is valid

### Metrics Not Showing

- Check metrics icon paths
- Verify icons are in `assets/composition/metrics/`
- Ensure metrics calculation is enabled

### Simulation Not Working

- Check simulation element paths
- Verify elements are in `assets/composition/simulation/`
- Ensure simulation system is enabled

### Validation Not Functioning

- Check validation indicator paths
- Verify indicators are in `assets/composition/validation/`
- Ensure validation system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
