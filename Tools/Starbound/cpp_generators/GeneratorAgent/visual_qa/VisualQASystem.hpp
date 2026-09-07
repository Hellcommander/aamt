#pragma once

#include <opencv2/opencv.hpp"
#include <opencv2/quality.hpp"
#include <filesystem>
#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include "core/Log.hpp"

namespace fs = std::filesystem;

namespace MagiTech {
namespace VisualQA {

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
    int frameIndex;
    std::string baselinePath;
    std::string testPath;
    std::string diffPath;
    ImageScore score;
    bool passed;
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
    bool generateBaseline(const AssetTestConfig& config);
    
    // Image comparison
    ImageScore compareImages(const cv::Mat& baseline, const cv::Mat& test);
    cv::Mat generateDiffImage(const cv::Mat& baseline, const cv::Mat& test);
    
    // Utility functions
    cv::Mat loadImage(const fs::path& path);
    bool saveImage(const cv::Mat& img, const fs::path& path);
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
    cv::Mat preprocessImage(const cv::Mat& img);
    double computePSNR(const cv::Mat& img1, const cv::Mat& img2);
    double computeSSIM(const cv::Mat& img1, const cv::Mat& img2);
    double computeHistogramCorrelation(const cv::Mat& img1, const cv::Mat& img2);
    double computeShapeDifference(const cv::Mat& img1, const cv::Mat& img2);
    double computeColorDistance(const cv::Mat& img1, const cv::Mat& img2);
    double computeEdgeSimilarity(const cv::Mat& img1, const cv::Mat& img2);
    std::vector<cv::Point> findLargestContour(const cv::Mat& img);
};

// Utility functions
namespace Utils {
    // Color space conversions
    cv::Mat rgbaToBgr(const cv::Mat& rgba);
    cv::Mat bgrToHsv(const cv::Mat& bgr);
    
    // Image processing
    cv::Mat normalizeImage(const cv::Mat& img);
    cv::Mat applyGaussianBlur(const cv::Mat& img, double sigma = 1.0);
    cv::Mat detectEdges(const cv::Mat& img);
    
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
