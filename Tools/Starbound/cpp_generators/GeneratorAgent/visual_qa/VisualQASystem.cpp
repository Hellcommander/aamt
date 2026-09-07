#include "VisualQASystem.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <chrono>

namespace MagiTech {
namespace VisualQA {

// ImageScore implementation
bool ImageScore::passes() const {
    return psnr >= PASS_PSNR &&
           ssim >= PASS_SSIM &&
           histCorr >= PASS_HIST &&
           shapeDiff <= PASS_SHAPE &&
           colorDistance <= PASS_COLOR &&
           edgeSimilarity >= PASS_EDGE;
}

std::string ImageScore::getReport() const {
    std::ostringstream oss;
    oss << "PSNR: " << std::fixed << std::setprecision(2) << psnr << " dB"
        << " | SSIM: " << std::fixed << std::setprecision(3) << ssim
        << " | HistCorr: " << std::fixed << std::setprecision(3) << histCorr
        << " | ShapeDiff: " << std::fixed << std::setprecision(3) << shapeDiff
        << " | ColorDist: " << std::fixed << std::setprecision(3) << colorDistance
        << " | EdgeSim: " << std::fixed << std::setprecision(3) << edgeSimilarity
        << " | Quality: " << std::fixed << std::setprecision(3) << qualityScore;
    return oss.str();
}

// TestResult implementation
std::string TestResult::getReport() const {
    std::ostringstream oss;
    oss << "Asset: " << assetName << " Frame: " << frameIndex
        << " | " << (passed ? "PASS" : "FAIL") << " | " << score.getReport();
    if (!passed && !failureReason.empty()) {
        oss << " | Reason: " << failureReason;
    }
    return oss.str();
}

// VisualQASystem implementation
VisualQASystem::VisualQASystem() {
    Log::info("Visual QA System initialized");
}

VisualQASystem::~VisualQASystem() {
    Log::info("Visual QA System shutdown");
}

bool VisualQASystem::runAssetTest(const AssetTestConfig& config) {
    Log::info("Running visual QA test for asset: {}", config.assetName);
    
    if (!ensureDirectories()) {
        Log::error("Failed to create required directories");
        return false;
    }
    
    m_lastResults.clear();
    bool allPassed = true;
    
    // Determine frame count
    int frameCount = config.frameCount;
    if (!config.seeds.empty()) {
        frameCount = static_cast<int>(config.seeds.size());
    }
    
    for (int i = 0; i < frameCount; ++i) {
        TestResult result;
        result.assetName = config.assetName;
        result.frameIndex = i;
        
        // Construct file paths
        std::string frameName = std::to_string(i);
        if (!config.seeds.empty()) {
            frameName = config.seeds[i];
        }
        
        fs::path baselinePath = m_baselineDir / config.category / config.assetName / (frameName + ".png");
        fs::path testPath = m_testDir / config.category / config.assetName / (frameName + ".png");
        fs::path diffPath = m_reportDir / config.category / config.assetName / (frameName + "_diff.png");
        
        result.baselinePath = baselinePath.string();
        result.testPath = testPath.string();
        result.diffPath = diffPath.string();
        
        // Check if files exist
        if (!fs::exists(baselinePath)) {
            result.passed = false;
            result.failureReason = "Baseline file not found: " + baselinePath.string();
            m_lastResults.push_back(result);
            allPassed = false;
            continue;
        }
        
        if (!fs::exists(testPath)) {
            result.passed = false;
            result.failureReason = "Test file not found: " + testPath.string();
            m_lastResults.push_back(result);
            allPassed = false;
            continue;
        }
        
        // Load and compare images
        cv::Mat baselineImg = loadImage(baselinePath);
        cv::Mat testImg = loadImage(testPath);
        
        if (baselineImg.empty() || testImg.empty()) {
            result.passed = false;
            result.failureReason = "Failed to load images";
            m_lastResults.push_back(result);
            allPassed = false;
            continue;
        }
        
        // Compare images
        result.score = compareImages(baselineImg, testImg);
        
        // Check against thresholds
        result.passed = result.score.psnr >= config.minPSNR &&
                       result.score.ssim >= config.minSSIM &&
                       result.score.histCorr >= config.minHistCorr &&
                       result.score.shapeDiff <= config.maxShapeDiff &&
                       result.score.colorDistance <= config.maxColorDistance &&
                       result.score.edgeSimilarity >= config.minEdgeSimilarity;
        
        // Generate diff image if failed
        if (!result.passed && m_generateDiffImages) {
            Utils::ensureDirectory(diffPath.parent_path());
            cv::Mat diffImg = generateDiffImage(baselineImg, testImg);
            saveImage(diffImg, diffPath);
        }
        
        // Log result
        Log::info("Frame {}: {}", i, result.getReport());
        
        m_lastResults.push_back(result);
        if (!result.passed) {
            allPassed = false;
        }
    }
    
    double passRate = getPassRate();
    Log::info("Asset {} test complete. Pass rate: {:.1f}%", config.assetName, passRate * 100.0);
    
    return allPassed;
}

bool VisualQASystem::runBatchTest(const std::vector<AssetTestConfig>& configs) {
    Log::info("Running batch visual QA test for {} assets", configs.size());
    
    bool allPassed = true;
    std::vector<TestResult> allResults;
    
    for (const auto& config : configs) {
        if (!runAssetTest(config)) {
            allPassed = false;
        }
        allResults.insert(allResults.end(), m_lastResults.begin(), m_lastResults.end());
    }
    
    m_lastResults = allResults;
    
    // Generate HTML report
    if (m_generateHTMLReport) {
        Utils::ensureDirectory(m_reportDir);
        std::string htmlReport = generateHTMLReport(allResults);
        fs::path reportPath = m_reportDir / "visual_qa_report.html";
        std::ofstream reportFile(reportPath);
        if (reportFile.is_open()) {
            reportFile << htmlReport;
            Log::info("HTML report generated: {}", reportPath.string());
        }
    }
    
    return allPassed;
}

bool VisualQASystem::generateBaseline(const AssetTestConfig& config) {
    Log::info("Generating baseline for asset: {}", config.assetName);
    
    fs::path baselinePath = m_baselineDir / config.category / config.assetName;
    Utils::ensureDirectory(baselinePath);
    
    // This would typically call your asset generator with specific seeds
    // For now, we'll just create placeholder files
    for (int i = 0; i < config.frameCount; ++i) {
        std::string frameName = std::to_string(i);
        if (!config.seeds.empty() && i < config.seeds.size()) {
            frameName = config.seeds[i];
        }
        
        fs::path framePath = baselinePath / (frameName + ".png");
        
        // Create a placeholder image (in real implementation, this would be generated)
        cv::Mat placeholder(256, 256, CV_8UC4, cv::Scalar(100, 150, 200, 255));
        saveImage(placeholder, framePath);
    }
    
    Log::info("Baseline generated for {} frames", config.frameCount);
    return true;
}

ImageScore VisualQASystem::compareImages(const cv::Mat& baseline, const cv::Mat& test) {
    ImageScore score;
    
    // Ensure images are the same size
    cv::Mat baselineResized, testResized;
    cv::resize(baseline, baselineResized, cv::Size(256, 256));
    cv::resize(test, testResized, cv::Size(256, 256));
    
    // Preprocess images
    cv::Mat baselineProc = preprocessImage(baselineResized);
    cv::Mat testProc = preprocessImage(testResized);
    
    // Compute metrics
    score.psnr = computePSNR(baselineProc, testProc);
    score.ssim = computeSSIM(baselineProc, testProc);
    score.histCorr = computeHistogramCorrelation(baselineProc, testProc);
    score.shapeDiff = computeShapeDifference(baselineProc, testProc);
    score.colorDistance = computeColorDistance(baselineProc, testProc);
    score.edgeSimilarity = computeEdgeSimilarity(baselineProc, testProc);
    
    // Compute aggregated quality score
    score.qualityScore = (score.psnr / 50.0) * 0.2 +           // PSNR weight
                        score.ssim * 0.3 +                       // SSIM weight
                        score.histCorr * 0.2 +                   // Histogram weight
                        (1.0 - score.shapeDiff) * 0.15 +        // Shape weight
                        (1.0 - score.colorDistance) * 0.1 +     // Color weight
                        score.edgeSimilarity * 0.05;             // Edge weight
    
    score.qualityScore = std::clamp(score.qualityScore, 0.0, 1.0);
    
    return score;
}

cv::Mat VisualQASystem::generateDiffImage(const cv::Mat& baseline, const cv::Mat& test) {
    cv::Mat diff, heatmap;
    
    // Compute absolute difference
    cv::absdiff(baseline, test, diff);
    
    // Convert to grayscale for heatmap
    cv::Mat grayDiff;
    if (diff.channels() == 4) {
        cv::cvtColor(diff, grayDiff, cv::COLOR_RGBA2GRAY);
    } else if (diff.channels() == 3) {
        cv::cvtColor(diff, grayDiff, cv::COLOR_BGR2GRAY);
    } else {
        grayDiff = diff;
    }
    
    // Normalize and apply color map
    cv::normalize(grayDiff, grayDiff, 0, 255, cv::NORM_MINMAX);
    cv::applyColorMap(grayDiff, heatmap, cv::COLORMAP_JET);
    
    // Overlay original images for context
    cv::Mat result;
    cv::hconcat(baseline, test, result);
    cv::Mat diffResized;
    cv::resize(heatmap, diffResized, cv::Size(result.cols, result.rows));
    cv::hconcat(result, diffResized, result);
    
    return result;
}

cv::Mat VisualQASystem::loadImage(const fs::path& path) {
    cv::Mat img = cv::imread(path.string(), cv::IMREAD_UNCHANGED);
    if (img.empty()) {
        Log::error("Failed to load image: {}", path.string());
        return cv::Mat();
    }
    
    // Convert RGBA to BGR if needed
    if (img.channels() == 4) {
        cv::Mat bgr;
        cv::cvtColor(img, bgr, cv::COLOR_RGBA2BGR);
        return bgr;
    }
    
    return img;
}

bool VisualQASystem::saveImage(const cv::Mat& img, const fs::path& path) {
    Utils::ensureDirectory(path.parent_path());
    return cv::imwrite(path.string(), img);
}

std::string VisualQASystem::generateHTMLReport(const std::vector<TestResult>& results) {
    std::ostringstream html;
    
    // Count statistics
    int totalTests = static_cast<int>(results.size());
    int passedTests = 0;
    int failedTests = 0;
    
    for (const auto& result : results) {
        if (result.passed) passedTests++;
        else failedTests++;
    }
    
    double passRate = totalTests > 0 ? (double)passedTests / totalTests : 0.0;
    
    // Generate HTML
    html << "<!DOCTYPE html>\n";
    html << "<html>\n<head>\n";
    html << "<title>Visual QA Report</title>\n";
    html << "<style>\n";
    html << "body { font-family: Arial, sans-serif; margin: 20px; }\n";
    html << ".header { background: #f0f0f0; padding: 20px; border-radius: 5px; }\n";
    html << ".summary { margin: 20px 0; }\n";
    html << ".test-result { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }\n";
    html << ".passed { background: #d4edda; border-color: #c3e6cb; }\n";
    html << ".failed { background: #f8d7da; border-color: #f5c6cb; }\n";
    html << ".metrics { font-family: monospace; font-size: 12px; }\n";
    html << ".diff-image { max-width: 100%; height: auto; }\n";
    html << "</style>\n</head>\n<body>\n";
    
    // Header
    html << "<div class='header'>\n";
    html << "<h1>Visual QA Report</h1>\n";
    html << "<p>Generated: " << Utils::generateTimestamp() << "</p>\n";
    html << "</div>\n";
    
    // Summary
    html << "<div class='summary'>\n";
    html << "<h2>Summary</h2>\n";
    html << "<p>Total Tests: " << totalTests << "</p>\n";
    html << "<p>Passed: " << passedTests << " (" << std::fixed << std::setprecision(1) << (passRate * 100.0) << "%)</p>\n";
    html << "<p>Failed: " << failedTests << "</p>\n";
    html << "</div>\n";
    
    // Results
    html << "<h2>Test Results</h2>\n";
    for (const auto& result : results) {
        html << "<div class='test-result " << (result.passed ? "passed" : "failed") << "'>\n";
        html << "<h3>" << result.assetName << " - Frame " << result.frameIndex << "</h3>\n";
        html << "<p>Status: " << Utils::getStatusEmoji(result.passed) << " " << (result.passed ? "PASS" : "FAIL") << "</p>\n";
        html << "<div class='metrics'>" << result.score.getReport() << "</div>\n";
        
        if (!result.passed) {
            html << "<p>Failure Reason: " << result.failureReason << "</p>\n";
            if (fs::exists(result.diffPath)) {
                html << "<img src='" << result.diffPath << "' alt='Diff' class='diff-image'>\n";
            }
        }
        
        html << "</div>\n";
    }
    
    html << "</body>\n</html>\n";
    
    return html.str();
}

double VisualQASystem::getPassRate() const {
    if (m_lastResults.empty()) return 0.0;
    
    int passed = 0;
    for (const auto& result : m_lastResults) {
        if (result.passed) passed++;
    }
    
    return (double)passed / m_lastResults.size();
}

// Private methods
bool VisualQASystem::ensureDirectories() {
    return Utils::ensureDirectory(m_baselineDir) &&
           Utils::ensureDirectory(m_testDir) &&
           Utils::ensureDirectory(m_reportDir);
}

cv::Mat VisualQASystem::preprocessImage(const cv::Mat& img) {
    cv::Mat processed = img.clone();
    
    // Convert to BGR if needed
    if (processed.channels() == 4) {
        cv::cvtColor(processed, processed, cv::COLOR_RGBA2BGR);
    }
    
    // Normalize
    cv::Mat normalized;
    cv::normalize(processed, normalized, 0, 255, cv::NORM_MINMAX);
    
    return normalized;
}

double VisualQASystem::computePSNR(const cv::Mat& img1, const cv::Mat& img2) {
    return cv::PSNR(img1, img2);
}

double VisualQASystem::computeSSIM(const cv::Mat& img1, const cv::Mat& img2) {
    cv::Mat ssimMap;
    auto qualitySsim = cv::quality::QualitySSIM(img1, img2, cv::Mat(), ssimMap);
    return qualitySsim.compute(ssimMap)[0];
}

double VisualQASystem::computeHistogramCorrelation(const cv::Mat& img1, const cv::Mat& img2) {
    std::vector<cv::Mat> channels1, channels2;
    cv::split(img1, channels1);
    cv::split(img2, channels2);
    
    double totalCorr = 0.0;
    for (size_t i = 0; i < channels1.size(); ++i) {
        cv::Mat hist1, hist2;
        int histSize = 256;
        float range[] = {0, 256};
        const float* histRange = {range};
        
        cv::calcHist(&channels1[i], 1, nullptr, cv::Mat(), hist1, 1, &histSize, &histRange);
        cv::calcHist(&channels2[i], 1, nullptr, cv::Mat(), hist2, 1, &histSize, &histRange);
        
        totalCorr += cv::compareHist(hist1, hist2, cv::HISTCMP_CORREL);
    }
    
    return totalCorr / channels1.size();
}

double VisualQASystem::computeShapeDifference(const cv::Mat& img1, const cv::Mat& img2) {
    cv::Mat gray1, gray2;
    cv::cvtColor(img1, gray1, cv::COLOR_BGR2GRAY);
    cv::cvtColor(img2, gray2, cv::COLOR_BGR2GRAY);
    
    cv::Mat binary1, binary2;
    cv::threshold(gray1, binary1, 10, 255, cv::THRESH_BINARY);
    cv::threshold(gray2, binary2, 10, 255, cv::THRESH_BINARY);
    
    std::vector<std::vector<cv::Point>> contours1, contours2;
    cv::findContours(binary1, contours1, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    cv::findContours(binary2, contours2, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    if (contours1.empty() || contours2.empty()) {
        return 1.0; // Maximum difference if no contours found
    }
    
    // Find largest contours
    auto largest1 = *std::max_element(contours1.begin(), contours1.end(),
                                     [](const auto& a, const auto& b) { return a.size() < b.size(); });
    auto largest2 = *std::max_element(contours2.begin(), contours2.end(),
                                     [](const auto& a, const auto& b) { return a.size() < b.size(); });
    
    return cv::matchShapes(largest1, largest2, cv::CONTOURS_MATCH_I1, 0.0);
}

double VisualQASystem::computeColorDistance(const cv::Mat& img1, const cv::Mat& img2) {
    cv::Mat hsv1, hsv2;
    cv::cvtColor(img1, hsv1, cv::COLOR_BGR2HSV);
    cv::cvtColor(img2, hsv2, cv::COLOR_BGR2HSV);
    
    cv::Mat diff;
    cv::absdiff(hsv1, hsv2, diff);
    
    cv::Scalar meanDiff = cv::mean(diff);
    return (meanDiff[0] + meanDiff[1] + meanDiff[2]) / 3.0 / 255.0;
}

double VisualQASystem::computeEdgeSimilarity(const cv::Mat& img1, const cv::Mat& img2) {
    cv::Mat edges1 = Utils::detectEdges(img1);
    cv::Mat edges2 = Utils::detectEdges(img2);
    
    cv::Mat diff;
    cv::absdiff(edges1, edges2, diff);
    
    double totalPixels = diff.rows * diff.cols;
    double differentPixels = cv::countNonZero(diff);
    
    return 1.0 - (differentPixels / totalPixels);
}

// Utils implementation
namespace Utils {

cv::Mat rgbaToBgr(const cv::Mat& rgba) {
    cv::Mat bgr;
    cv::cvtColor(rgba, bgr, cv::COLOR_RGBA2BGR);
    return bgr;
}

cv::Mat bgrToHsv(const cv::Mat& bgr) {
    cv::Mat hsv;
    cv::cvtColor(bgr, hsv, cv::COLOR_BGR2HSV);
    return hsv;
}

cv::Mat normalizeImage(const cv::Mat& img) {
    cv::Mat normalized;
    cv::normalize(img, normalized, 0, 255, cv::NORM_MINMAX);
    return normalized;
}

cv::Mat applyGaussianBlur(const cv::Mat& img, double sigma) {
    cv::Mat blurred;
    int kernelSize = static_cast<int>(sigma * 6 + 1) | 1; // Ensure odd
    cv::GaussianBlur(img, blurred, cv::Size(kernelSize, kernelSize), sigma);
    return blurred;
}

cv::Mat detectEdges(const cv::Mat& img) {
    cv::Mat gray, edges;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    cv::Canny(gray, edges, 50, 150);
    return edges;
}

bool ensureDirectory(const fs::path& path) {
    if (!fs::exists(path)) {
        return fs::create_directories(path);
    }
    return true;
}

std::string getFileExtension(const fs::path& path) {
    return path.extension().string();
}

bool isValidImageFile(const fs::path& path) {
    std::string ext = getFileExtension(path);
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    return ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".tga";
}

std::string formatScore(double score, int precision) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(precision) << score;
    return oss.str();
}

std::string getStatusEmoji(bool passed) {
    return passed ? "✅" : "❌";
}

std::string generateTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

} // namespace Utils

} // namespace VisualQA
} // namespace MagiTech 
