# Visual QA System - Automated Visual Regression & Quality Checks

A comprehensive system for ensuring procedural asset generation maintains consistent quality and style across builds through automated visual regression testing.

## 🎯 **Overview**

The Visual QA System provides:
- **Automated image comparison** using multiple quality metrics
- **Baseline generation and management** for reference assets
- **Visual diff generation** with heatmaps for failed tests
- **HTML reporting** with detailed analysis and statistics
- **CI/CD integration** for automated quality gates
- **Lua scripting** for custom test configurations

## 📁 **File Structure**

```
visual_qa/
├── VisualQASystem.hpp          # Main system header
├── VisualQASystem.cpp          # Complete implementation
├── VisualQALuaBindings.hpp     # Lua bindings header
├── VisualQALuaBindings.cpp     # Lua integration
├── scripts/visual_qa_example.lua # Usage examples
└── README.md                   # This documentation
```

## 🔧 **Core Components**

### **ImageScore Structure**
```cpp
struct ImageScore {
    double psnr = 0.0;           // Peak Signal-to-Noise Ratio
    double ssim = 0.0;           // Structural Similarity Index
    double histCorr = 0.0;       // Histogram Correlation
    double shapeDiff = 0.0;      // Shape/Contour Difference
    double colorDistance = 0.0;  // Color space distance
    double edgeSimilarity = 0.0; // Edge detection similarity
    double qualityScore = 0.0;   // Aggregated score (0.0-1.0)
};
```

### **AssetTestConfig Structure**
```cpp
struct AssetTestConfig {
    std::string assetName;        // Asset identifier
    std::string category;         // "spell", "mech", "texture", etc.
    int frameCount = 1;           // Number of frames to test
    std::vector<std::string> seeds; // Specific seeds to test
    bool generateBaseline = false; // Generate new baseline
    double tolerance = 0.05;      // Tolerance for variations
    
    // Quality thresholds (can override defaults)
    double minPSNR = 30.0;
    double minSSIM = 0.90;
    double minHistCorr = 0.95;
    double maxShapeDiff = 0.1;
    double maxColorDistance = 0.05;
    double minEdgeSimilarity = 0.85;
};
```

## 📊 **Quality Metrics**

### **1. PSNR (Peak Signal-to-Noise Ratio)**
- **What it measures**: Pixel-wise mean squared error
- **Range**: 0-∞ dB (higher is better)
- **Pass threshold**: > 30 dB
- **Use case**: Overall image similarity

### **2. SSIM (Structural Similarity Index)**
- **What it measures**: Perceptual similarity (luminance, contrast, structure)
- **Range**: 0.0-1.0 (higher is better)
- **Pass threshold**: > 0.90
- **Use case**: Visual quality preservation

### **3. Histogram Correlation**
- **What it measures**: Color distribution similarity
- **Range**: -1.0 to 1.0 (higher is better)
- **Pass threshold**: > 0.95
- **Use case**: Color palette consistency

### **4. Shape Difference**
- **What it measures**: Contour/silhouette similarity
- **Range**: 0.0-1.0 (lower is better)
- **Pass threshold**: < 0.1
- **Use case**: Object shape preservation

### **5. Color Distance**
- **What it measures**: HSV color space difference
- **Range**: 0.0-1.0 (lower is better)
- **Pass threshold**: < 0.05
- **Use case**: Color accuracy

### **6. Edge Similarity**
- **What it measures**: Edge detection similarity
- **Range**: 0.0-1.0 (higher is better)
- **Pass threshold**: > 0.85
- **Use case**: Detail preservation

## 🚀 **Usage Examples**

### **C++ Usage**
```cpp
#include "VisualQASystem.hpp"

// Create Visual QA system
VisualQA::VisualQASystem qa;

// Configure directories
qa.setBaselineDir("baseline");
qa.setTestDir("test");
qa.setReportDir("reports");

// Test a single asset
VisualQA::AssetTestConfig config;
config.assetName = "fireball";
config.category = "spell";
config.frameCount = 16;

bool passed = qa.runAssetTest(config);

// Get results
const auto& results = qa.getLastResults();
double passRate = qa.getPassRate();
```

### **Lua Usage**
```lua
-- Configure system
VisualQA.configure("baseline", "test", "reports")

-- Test different asset types
local spellPassed = VisualQA.testSpell("fireball", 16)
local mechPassed = VisualQA.testMech("worm_mech", 8)
local texturePassed = VisualQA.testTexture("noise_texture")

-- Get detailed results
local results = VisualQA.getResults()
local passRate = VisualQA.getPassRate()

-- Custom configuration
local config = AssetTestConfig()
config.assetName = "custom_asset"
config.category = "spell"
config.frameCount = 8
config.minPSNR = 25.0  -- Lower threshold
config.minSSIM = 0.85  -- Lower threshold

local passed = VisualQA.getInstance():runAssetTest(config)
```

## 📋 **Directory Structure**

### **Baseline Directory**
```
baseline/
├── spell/
│   ├── fireball/
│   │   ├── 0.png
│   │   ├── 1.png
│   │   └── ...
│   └── ice_shard/
│       └── ...
├── mech/
│   ├── worm_mech/
│   └── snake_mech/
└── texture/
    └── noise_texture/
```

### **Test Directory**
```
test/
├── spell/
│   ├── fireball/
│   │   ├── 0.png
│   │   ├── 1.png
│   │   └── ...
│   └── ice_shard/
└── mech/
    └── worm_mech/
```

### **Reports Directory**
```
reports/
├── visual_qa_report.html
├── spell/
│   ├── fireball/
│   │   ├── 0_diff.png
│   │   ├── 1_diff.png
│   │   └── ...
│   └── ice_shard/
└── mech/
    └── worm_mech/
```

## 🎨 **Visual Diff Generation**

When tests fail, the system generates comprehensive diff images:

1. **Baseline Image** (left)
2. **Test Image** (center)
3. **Difference Heatmap** (right)

The heatmap uses a color-coded system:
- **Blue**: Minimal differences
- **Green**: Moderate differences
- **Yellow**: Significant differences
- **Red**: Major differences

## 📊 **HTML Reporting**

The system generates detailed HTML reports with:

### **Summary Section**
- Total tests run
- Pass/fail counts
- Overall pass rate
- Generation timestamp

### **Detailed Results**
- Individual test results
- Quality metrics breakdown
- Failure reasons
- Embedded diff images
- Threshold comparisons

### **Example Report Structure**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Visual QA Report</title>
    <style>/* CSS styling */</style>
</head>
<body>
    <div class="header">
        <h1>Visual QA Report</h1>
        <p>Generated: 2024-01-15 14:30:25</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: 24</p>
        <p>Passed: 22 (91.7%)</p>
        <p>Failed: 2</p>
    </div>
    
    <h2>Test Results</h2>
    <div class="test-result passed">
        <h3>fireball - Frame 0</h3>
        <p>Status: ✅ PASS</p>
        <div class="metrics">PSNR: 35.2 dB | SSIM: 0.95...</div>
    </div>
    
    <div class="test-result failed">
        <h3>fireball - Frame 5</h3>
        <p>Status: ❌ FAIL</p>
        <div class="metrics">PSNR: 28.1 dB | SSIM: 0.87...</div>
        <p>Failure Reason: SSIM below threshold</p>
        <img src="spell/fireball/5_diff.png" alt="Diff" class="diff-image">
    </div>
</body>
</html>
```

## 🔧 **CI/CD Integration**

### **GitHub Actions Example**
```yaml
name: Visual QA Tests
on: [push, pull_request]

jobs:
  visual-qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup OpenCV
        run: |
          sudo apt-get update
          sudo apt-get install libopencv-dev
      
      - name: Build Visual QA
        run: |
          mkdir build && cd build
          cmake ..
          make visual_qa_tests
      
      - name: Run Visual QA Tests
        run: |
          ./visual_qa_tests
          if [ $? -ne 0 ]; then
            echo "Visual QA tests failed"
            exit 1
          fi
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: visual-qa-reports
          path: reports/
```

### **CMake Integration**
```cmake
# Add Visual QA tests
add_executable(visual_qa_tests
    tests/visual_qa_test.cpp
    cpp_backend/core/modules/visual_qa/VisualQASystem.cpp
)

target_link_libraries(visual_qa_tests
    opencv_core
    opencv_imgproc
    opencv_imgcodecs
    opencv_quality
)

# Add to CTest
add_test(NAME VisualQA COMMAND visual_qa_tests)
```

## 🛠️ **Configuration Options**

### **Quality Thresholds**
```cpp
// Standard thresholds
constexpr double PASS_PSNR = 30.0;        // dB
constexpr double PASS_SSIM = 0.90;        // 0.0-1.0
constexpr double PASS_HIST = 0.95;        // 0.0-1.0
constexpr double PASS_SHAPE = 0.1;        // 0.0-1.0
constexpr double PASS_COLOR = 0.05;       // 0.0-1.0
constexpr double PASS_EDGE = 0.85;        // 0.0-1.0

// Custom thresholds for specific assets
config.minPSNR = 25.0;  // Lower for noisy assets
config.minSSIM = 0.85;  // Lower for artistic assets
```

### **Directory Configuration**
```cpp
qa.setBaselineDir("baseline");     // Reference images
qa.setTestDir("test");            // Generated images
qa.setReportDir("reports");       // Output reports
```

### **Tolerance Settings**
```cpp
qa.setTolerance(0.05);  // 5% tolerance for variations
```

## 📈 **Performance Features**

### **Optimization Techniques**
- **Image preprocessing** for consistent comparison
- **Efficient memory management** for large image sets
- **Parallel processing** for batch tests
- **Caching** of computed metrics

### **Memory Management**
- **Automatic cleanup** of temporary images
- **LRU caching** for frequently accessed baselines
- **Streaming** for large image sequences

### **Scalability**
- **Batch processing** for multiple assets
- **Incremental testing** for changed assets only
- **Distributed testing** across multiple machines

## 🔮 **Future Extensions**

### **Planned Features**
- **GPU acceleration** using CUDA/OpenCL
- **Machine learning** quality assessment
- **Real-time monitoring** during asset generation
- **Advanced diff visualization** with 3D heatmaps
- **Integration with asset generators** for automatic testing

### **Advanced Metrics**
- **Perceptual hashing** for rapid comparison
- **Deep learning** similarity scoring
- **Temporal consistency** for animations
- **Style transfer** detection

### **Integration Points**
- **Asset generation pipelines** for automatic testing
- **Version control** for baseline management
- **Cloud storage** for distributed testing
- **Web dashboard** for real-time monitoring

## 📝 **Best Practices**

### **Baseline Management**
1. **Version control** baseline images
2. **Document** baseline generation parameters
3. **Review** baseline updates carefully
4. **Tag** baseline versions with releases

### **Test Configuration**
1. **Use appropriate thresholds** for asset types
2. **Test representative samples** of asset variations
3. **Include edge cases** in test suites
4. **Regular threshold reviews** based on results

### **CI/CD Integration**
1. **Fail fast** on critical quality issues
2. **Generate reports** for all test runs
3. **Archive results** for trend analysis
4. **Notify stakeholders** of quality regressions

## 🎯 **Use Cases**

### **Spell Asset Testing**
- **Frame consistency** across animation sequences
- **Color palette** preservation
- **Effect intensity** validation
- **Particle system** stability

### **Mech Asset Testing**
- **Mesh geometry** consistency
- **Texture mapping** accuracy
- **Animation rigging** stability
- **Material appearance** preservation

### **Texture Asset Testing**
- **Noise pattern** consistency
- **Color gradient** accuracy
- **Seamless tiling** validation
- **Compression artifact** detection

---

**Status**: ✅ **Complete Implementation**
**Next Steps**: Integrate with asset generation pipelines and add GPU acceleration. 