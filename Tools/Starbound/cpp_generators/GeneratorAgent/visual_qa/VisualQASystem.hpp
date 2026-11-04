#pragma once

// Visual regression QA for generated assets.
// OpenCV is not available to the backend build (only unbuilt sources are vendored), so the image
// container and every metric (PSNR, SSIM, histogram correlation, Hu-moment shape match, HSV colour
// distance, Canny edge similarity) are implemented here on a small 8-bit image type. PNG/JPG/TGA/BMP
// files are read with stb_image and written (PNG) with stb_image_write.

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include "core/Log.hpp"

namespace fs = std::filesystem;

namespace MagiTech {
namespace VisualQA {

// 8-bit interleaved image (1 = gray, 3 = BGR, 4 = BGRA), row-major, no padding.
struct Image {
    int width = 0;
    int height = 0;
    int channels = 0;
    std::vector<uint8_t> data;

    Image() = default;
    Image(int w, int h, int c, uint8_t fill = 0)
        : width(w), height(h), channels(c), data(static_cast<size_t>(w) * h * c, fill) {}

    bool empty() const { return width <= 0 || height <= 0 || channels <= 0 || data.empty(); }
    size_t pixelCount() const { return static_cast<size_t>(width) * height; }
    uint8_t* ptr(int x, int y) { return data.data() + (static_cast<size_t>(y) * width + x) * channels; }
    const uint8_t* ptr(int x, int y) const { return data.data() + (static_cast<size_t>(y) * width + x) * channels; }
    uint8_t& at(int x, int y, int c) { return ptr(x, y)[c]; }
    uint8_t at(int x, int y, int c) const { return ptr(x, y)[c]; }
};

struct Point {
    int x = 0;
    int y = 0;
};

// Image comparison metrics structure
struct ImageScore {
    double psnr = 0.0;           // Peak Signal-to-Noise Ratio
    double ssim = 0.0;           // Structural Similarity Index
    double histCorr = 0.0;       // Histogram Correlation
    double shapeDiff = 0.0;      // Shape/Contour Difference
    double colorDistance = 0.0;  // Color space distance
    double edgeSimilarity = 0.0; // Edge detection similarity

    // Aggregated quality score (0.0 to 1.0)
    double qualityScore = 0.0;

    // Thresholds for pass/fail
    static constexpr double PASS_PSNR = 30.0;
    static constexpr double PASS_SSIM = 0.90;
    static constexpr double PASS_HIST = 0.95;
    static constexpr double PASS_SHAPE = 0.1;
    static constexpr double PASS_COLOR = 0.05;
    static constexpr double PASS_EDGE = 0.85;

    bool passes() const;
    std::string getReport() const;
};

// Asset test configuration
struct AssetTestConfig {
    std::string assetName;
    std::string category;           // "spell", "mech", "texture", etc.
    int frameCount = 1;             // Number of frames to test
    std::vector<std::string> seeds; // Specific seeds to test
    bool generateBaseline = false;  // Generate new baseline
    double tolerance = 0.05;        // Tolerance for variations

    // Quality thresholds (can override defaults)
    double minPSNR = ImageScore::PASS_PSNR;
    double minSSIM = ImageScore::PASS_SSIM;
    double minHistCorr = ImageScore::PASS_HIST;
    double maxShapeDiff = ImageScore::PASS_SHAPE;
    double maxColorDistance = ImageScore::PASS_COLOR;
    double minEdgeSimilarity = ImageScore::PASS_EDGE;
};

// Test result structure
struct TestResult {
    std::string assetName;
    int frameIndex = 0;
    std::string baselinePath;
    std::string testPath;
    std::string diffPath;
    ImageScore score;
    bool passed = false;
    std::string failureReason;

    std::string getReport() const;
};

// Visual QA System main class
class VisualQASystem {
public:
    VisualQASystem();
    ~VisualQASystem();

    // Configuration
    void setBaselineDir(const fs::path& path) { m_baselineDir = path; }
    void setTestDir(const fs::path& path) { m_testDir = path; }
    void setReportDir(const fs::path& path) { m_reportDir = path; }
    void setTolerance(double tolerance) { m_tolerance = tolerance; }

    // Core functionality
    bool runAssetTest(const AssetTestConfig& config);
    bool runBatchTest(const std::vector<AssetTestConfig>& configs);
    // Copies the current test renders of the asset into the baseline directory.
    bool generateBaseline(const AssetTestConfig& config);

    // Image comparison
    ImageScore compareImages(const Image& baseline, const Image& test);
    Image generateDiffImage(const Image& baseline, const Image& test);

    // Utility functions
    Image loadImage(const fs::path& path);
    bool saveImage(const Image& img, const fs::path& path);
    std::string generateHTMLReport(const std::vector<TestResult>& results);

    // Getters
    const std::vector<TestResult>& getLastResults() const { return m_lastResults; }
    double getPassRate() const;

private:
    // Directories
    fs::path m_baselineDir = "baseline";
    fs::path m_testDir = "test";
    fs::path m_reportDir = "reports";

    // Configuration
    double m_tolerance = 0.05;
    bool m_generateDiffImages = true;
    bool m_generateHTMLReport = true;

    // Results
    std::vector<TestResult> m_lastResults;

    // Internal methods
    bool ensureDirectories();
    Image preprocessImage(const Image& img);
    double computePSNR(const Image& img1, const Image& img2);
    double computeSSIM(const Image& img1, const Image& img2);
    double computeHistogramCorrelation(const Image& img1, const Image& img2);
    double computeShapeDifference(const Image& img1, const Image& img2);
    double computeColorDistance(const Image& img1, const Image& img2);
    double computeEdgeSimilarity(const Image& img1, const Image& img2);
    std::vector<Point> findLargestContour(const Image& img);
};

// Utility functions
namespace Utils {
    // Image file I/O (stb_image / stb_image_write); loaded images are BGR or BGRA.
    Image readImageFile(const fs::path& path);
    bool writeImageFile(const Image& img, const fs::path& path);

    // Color space conversions
    Image rgbaToBgr(const Image& rgba);
    Image bgraToBgr(const Image& bgra);
    Image bgrToHsv(const Image& bgr);   // OpenCV 8-bit convention: H in [0,180), S,V in [0,255]
    Image toGray(const Image& img);

    // Image processing
    Image resize(const Image& img, int width, int height);  // bilinear
    Image normalizeImage(const Image& img);                 // min-max stretch to [0,255]
    Image applyGaussianBlur(const Image& img, double sigma = 1.0);
    Image detectEdges(const Image& img);                    // Canny, thresholds 50/150
    Image absDiff(const Image& a, const Image& b);
    Image applyJetColorMap(const Image& gray);              // gray -> BGR heatmap
    Image hconcat(const Image& a, const Image& b);

    // File operations
    bool ensureDirectory(const fs::path& path);
    std::string getFileExtension(const fs::path& path);
    bool isValidImageFile(const fs::path& path);

    // Reporting
    std::string formatScore(double score, int precision = 3);
    std::string getStatusEmoji(bool passed);
    std::string generateTimestamp();
}

} // namespace VisualQA
} // namespace MagiTech
