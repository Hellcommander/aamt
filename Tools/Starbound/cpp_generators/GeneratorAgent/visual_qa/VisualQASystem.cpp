#include "VisualQASystem.hpp"
#include <stb_image.h>
#include <stb_image_write.h>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <ctime>
#include <limits>

namespace MagiTech {
namespace VisualQA {

namespace {

constexpr int kCompareSize = 256;

uint8_t clampByte(double v) {
    return static_cast<uint8_t>(std::clamp(std::lround(v), 0L, 255L));
}

// Single-channel double plane used by the SSIM computation.
struct Plane {
    int width = 0;
    int height = 0;
    std::vector<double> v;
    Plane(int w, int h) : width(w), height(h), v(static_cast<size_t>(w) * h, 0.0) {}
    double& at(int x, int y) { return v[static_cast<size_t>(y) * width + x]; }
    double at(int x, int y) const { return v[static_cast<size_t>(y) * width + x]; }
};

std::vector<double> gaussianKernel(double sigma, int size) {
    std::vector<double> k(size);
    const int r = size / 2;
    double sum = 0.0;
    for (int i = 0; i < size; ++i) {
        const double d = i - r;
        k[i] = std::exp(-(d * d) / (2.0 * sigma * sigma));
        sum += k[i];
    }
    for (double& w : k) w /= sum;
    return k;
}

// Separable Gaussian filter with replicated borders.
Plane gaussianFilter(const Plane& src, const std::vector<double>& k) {
    const int r = static_cast<int>(k.size()) / 2;
    Plane tmp(src.width, src.height), out(src.width, src.height);
    for (int y = 0; y < src.height; ++y) {
        for (int x = 0; x < src.width; ++x) {
            double acc = 0.0;
            for (int i = -r; i <= r; ++i) {
                acc += k[i + r] * src.at(std::clamp(x + i, 0, src.width - 1), y);
            }
            tmp.at(x, y) = acc;
        }
    }
    for (int y = 0; y < src.height; ++y) {
        for (int x = 0; x < src.width; ++x) {
            double acc = 0.0;
            for (int i = -r; i <= r; ++i) {
                acc += k[i + r] * tmp.at(x, std::clamp(y + i, 0, src.height - 1));
            }
            out.at(x, y) = acc;
        }
    }
    return out;
}

Plane channelPlane(const Image& img, int c) {
    Plane p(img.width, img.height);
    for (int y = 0; y < img.height; ++y)
        for (int x = 0; x < img.width; ++x)
            p.at(x, y) = img.at(x, y, c);
    return p;
}

// Converts any supported layout to 3-channel BGR.
Image toBgr(const Image& img) {
    if (img.channels == 3) return img;
    Image out(img.width, img.height, 3);
    for (int y = 0; y < img.height; ++y) {
        for (int x = 0; x < img.width; ++x) {
            const uint8_t* s = img.ptr(x, y);
            uint8_t* d = out.ptr(x, y);
            if (img.channels >= 3) {
                d[0] = s[0]; d[1] = s[1]; d[2] = s[2];
            } else {
                d[0] = d[1] = d[2] = s[0];
            }
        }
    }
    return out;
}

// Binary mask of pixels whose gray value exceeds `threshold`.
std::vector<uint8_t> binaryMask(const Image& img, int threshold) {
    Image gray = Utils::toGray(img);
    std::vector<uint8_t> mask(gray.pixelCount());
    for (size_t i = 0; i < mask.size(); ++i) mask[i] = gray.data[i] > threshold ? 1 : 0;
    return mask;
}

// Largest 8-connected foreground component; returns its mask (empty when there is none).
std::vector<uint8_t> largestComponent(const std::vector<uint8_t>& mask, int width, int height) {
    std::vector<int> label(mask.size(), 0);
    int bestLabel = 0;
    size_t bestSize = 0;
    int next = 0;
    std::vector<int> stack;
    for (int start = 0; start < static_cast<int>(mask.size()); ++start) {
        if (!mask[start] || label[start]) continue;
        ++next;
        size_t size = 0;
        stack.push_back(start);
        label[start] = next;
        while (!stack.empty()) {
            const int idx = stack.back();
            stack.pop_back();
            ++size;
            const int x = idx % width, y = idx / width;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    const int nx = x + dx, ny = y + dy;
                    if ((dx == 0 && dy == 0) || nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
                    const int n = ny * width + nx;
                    if (mask[n] && !label[n]) {
                        label[n] = next;
                        stack.push_back(n);
                    }
                }
            }
        }
        if (size > bestSize) {
            bestSize = size;
            bestLabel = next;
        }
    }
    std::vector<uint8_t> out;
    if (bestLabel == 0) return out;
    out.assign(mask.size(), 0);
    for (size_t i = 0; i < mask.size(); ++i) out[i] = label[i] == bestLabel ? 1 : 0;
    return out;
}

// The seven Hu invariant moments of a binary region.
std::array<double, 7> huMoments(const std::vector<uint8_t>& region, int width, int height) {
    double m00 = 0, m10 = 0, m01 = 0;
    for (int y = 0; y < height; ++y)
        for (int x = 0; x < width; ++x)
            if (region[static_cast<size_t>(y) * width + x]) { m00 += 1; m10 += x; m01 += y; }
    std::array<double, 7> hu{};
    if (m00 <= 0) return hu;
    const double cx = m10 / m00, cy = m01 / m00;
    double mu20 = 0, mu02 = 0, mu11 = 0, mu30 = 0, mu03 = 0, mu21 = 0, mu12 = 0;
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (!region[static_cast<size_t>(y) * width + x]) continue;
            const double dx = x - cx, dy = y - cy;
            mu20 += dx * dx; mu02 += dy * dy; mu11 += dx * dy;
            mu30 += dx * dx * dx; mu03 += dy * dy * dy;
            mu21 += dx * dx * dy; mu12 += dx * dy * dy;
        }
    }
    const double s2 = std::pow(m00, 2.0), s3 = std::pow(m00, 2.5);
    const double n20 = mu20 / s2, n02 = mu02 / s2, n11 = mu11 / s2;
    const double n30 = mu30 / s3, n03 = mu03 / s3, n21 = mu21 / s3, n12 = mu12 / s3;
    const double t0 = n30 + n12, t1 = n21 + n03, q0 = n30 - 3 * n12, q1 = 3 * n21 - n03;
    hu[0] = n20 + n02;
    hu[1] = (n20 - n02) * (n20 - n02) + 4 * n11 * n11;
    hu[2] = q0 * q0 + q1 * q1;
    hu[3] = t0 * t0 + t1 * t1;
    hu[4] = q0 * t0 * (t0 * t0 - 3 * t1 * t1) + q1 * t1 * (3 * t0 * t0 - t1 * t1);
    hu[5] = (n20 - n02) * (t0 * t0 - t1 * t1) + 4 * n11 * t0 * t1;
    hu[6] = q1 * t0 * (t0 * t0 - 3 * t1 * t1) - q0 * t1 * (3 * t0 * t0 - t1 * t1);
    return hu;
}

} // namespace

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
    Log::info("VisualQA", "Running visual QA test for asset: {}", config.assetName);

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
        Image baselineImg = loadImage(baselinePath);
        Image testImg = loadImage(testPath);

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
        if (!result.passed) {
            result.failureReason = "Quality metrics below thresholds";
        }

        // Generate diff image if failed
        if (!result.passed && m_generateDiffImages) {
            Utils::ensureDirectory(diffPath.parent_path());
            Image diffImg = generateDiffImage(baselineImg, testImg);
            saveImage(diffImg, diffPath);
        }

        // Log result
        Log::info("VisualQA", "Frame {}: {}", i, result.getReport());

        m_lastResults.push_back(result);
        if (!result.passed) {
            allPassed = false;
        }
    }

    double passRate = getPassRate();
    Log::info("VisualQA", "Asset {} test complete. Pass rate: {:.1f}%", config.assetName, passRate * 100.0);

    return allPassed;
}

bool VisualQASystem::runBatchTest(const std::vector<AssetTestConfig>& configs) {
    Log::info("VisualQA", "Running batch visual QA test for {} assets", configs.size());

    bool allPassed = true;
    std::vector<TestResult> allResults;

    for (const auto& config : configs) {
        bool ok = config.generateBaseline ? generateBaseline(config) : runAssetTest(config);
        if (!ok) {
            allPassed = false;
        }
        if (!config.generateBaseline) {
            allResults.insert(allResults.end(), m_lastResults.begin(), m_lastResults.end());
        }
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
            Log::info("VisualQA", "HTML report generated: {}", reportPath.string());
        } else {
            Log::error("VisualQA", "Could not write HTML report: {}", reportPath.string());
        }
    }

    return allPassed;
}

bool VisualQASystem::generateBaseline(const AssetTestConfig& config) {
    Log::info("VisualQA", "Generating baseline for asset: {}", config.assetName);

    // The baseline is the asset's current rendered output: every test frame of the asset
    // (rendered by the asset pipeline into the test directory) is promoted to the baseline.
    const fs::path sourceDir = m_testDir / config.category / config.assetName;
    const fs::path baselinePath = m_baselineDir / config.category / config.assetName;
    if (!Utils::ensureDirectory(baselinePath)) {
        Log::error("VisualQA", "Could not create baseline directory: {}", baselinePath.string());
        return false;
    }

    const int frameCount = config.seeds.empty() ? config.frameCount : static_cast<int>(config.seeds.size());
    int written = 0;
    for (int i = 0; i < frameCount; ++i) {
        std::string frameName = std::to_string(i);
        if (!config.seeds.empty()) {
            frameName = config.seeds[static_cast<size_t>(i)];
        }

        const fs::path srcPath = sourceDir / (frameName + ".png");
        const fs::path framePath = baselinePath / (frameName + ".png");
        Image frame = loadImage(srcPath);
        if (frame.empty()) {
            Log::error("VisualQA", "No rendered frame to promote to baseline: {}", srcPath.string());
            continue;
        }
        if (saveImage(frame, framePath)) {
            ++written;
        }
    }

    Log::info("VisualQA", "Baseline generated for {} of {} frames", written, frameCount);
    return written == frameCount;
}

ImageScore VisualQASystem::compareImages(const Image& baseline, const Image& test) {
    ImageScore score;

    // Ensure images are the same size
    Image baselineResized = Utils::resize(toBgr(baseline), kCompareSize, kCompareSize);
    Image testResized = Utils::resize(toBgr(test), kCompareSize, kCompareSize);

    // Preprocess images
    Image baselineProc = preprocessImage(baselineResized);
    Image testProc = preprocessImage(testResized);

    // Compute metrics
    score.psnr = computePSNR(baselineProc, testProc);
    score.ssim = computeSSIM(baselineProc, testProc);
    score.histCorr = computeHistogramCorrelation(baselineProc, testProc);
    score.shapeDiff = computeShapeDifference(baselineProc, testProc);
    score.colorDistance = computeColorDistance(baselineProc, testProc);
    score.edgeSimilarity = computeEdgeSimilarity(baselineProc, testProc);

    // Compute aggregated quality score
    score.qualityScore = (std::min(score.psnr, 50.0) / 50.0) * 0.2 + // PSNR weight
                        score.ssim * 0.3 +                            // SSIM weight
                        score.histCorr * 0.2 +                        // Histogram weight
                        (1.0 - score.shapeDiff) * 0.15 +             // Shape weight
                        (1.0 - score.colorDistance) * 0.1 +          // Color weight
                        score.edgeSimilarity * 0.05;                  // Edge weight

    score.qualityScore = std::clamp(score.qualityScore, 0.0, 1.0);

    return score;
}

Image VisualQASystem::generateDiffImage(const Image& baseline, const Image& test) {
    // Bring both to the baseline's size and BGR layout
    Image base = toBgr(baseline);
    Image tst = Utils::resize(toBgr(test), base.width, base.height);

    // Absolute difference -> grayscale -> normalized heatmap
    Image grayDiff = Utils::normalizeImage(Utils::toGray(Utils::absDiff(base, tst)));
    Image heatmap = Utils::applyJetColorMap(grayDiff);

    // [baseline | test | diff heatmap] for context
    return Utils::hconcat(Utils::hconcat(base, tst), heatmap);
}

Image VisualQASystem::loadImage(const fs::path& path) {
    Image img = Utils::readImageFile(path);
    if (img.empty()) {
        Log::error("VisualQA", "Failed to load image: {}", path.string());
        return Image();
    }
    // Metrics work on BGR: drop alpha / expand gray
    return toBgr(img);
}

bool VisualQASystem::saveImage(const Image& img, const fs::path& path) {
    Utils::ensureDirectory(path.parent_path());
    if (!Utils::writeImageFile(img, path)) {
        Log::error("VisualQA", "Failed to save image: {}", path.string());
        return false;
    }
    return true;
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
    html << "<meta charset='utf-8'>\n";
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

Image VisualQASystem::preprocessImage(const Image& img) {
    // BGR + min-max normalization (removes global exposure differences)
    return Utils::normalizeImage(toBgr(img));
}

double VisualQASystem::computePSNR(const Image& img1, const Image& img2) {
    if (img1.data.size() != img2.data.size() || img1.data.empty()) return 0.0;
    double sse = 0.0;
    for (size_t i = 0; i < img1.data.size(); ++i) {
        const double d = static_cast<double>(img1.data[i]) - img2.data[i];
        sse += d * d;
    }
    const double mse = sse / static_cast<double>(img1.data.size());
    // Identical images: same cap OpenCV's cv::PSNR uses for 8-bit data
    if (mse <= 1e-10) return 361.20199909921956;
    return 20.0 * std::log10(255.0 / std::sqrt(mse));
}

double VisualQASystem::computeSSIM(const Image& img1, const Image& img2) {
    if (img1.width != img2.width || img1.height != img2.height || img1.channels != img2.channels || img1.empty()) {
        return 0.0;
    }
    // Wang et al. SSIM with an 11x11 Gaussian window (sigma 1.5), averaged over channels
    const double C1 = (0.01 * 255) * (0.01 * 255);
    const double C2 = (0.03 * 255) * (0.03 * 255);
    const auto k = gaussianKernel(1.5, 11);

    double total = 0.0;
    for (int c = 0; c < img1.channels; ++c) {
        Plane x = channelPlane(img1, c), y = channelPlane(img2, c);
        Plane xx(x.width, x.height), yy(x.width, x.height), xy(x.width, x.height);
        for (size_t i = 0; i < x.v.size(); ++i) {
            xx.v[i] = x.v[i] * x.v[i];
            yy.v[i] = y.v[i] * y.v[i];
            xy.v[i] = x.v[i] * y.v[i];
        }
        Plane mx = gaussianFilter(x, k), my = gaussianFilter(y, k);
        Plane sxx = gaussianFilter(xx, k), syy = gaussianFilter(yy, k), sxy = gaussianFilter(xy, k);

        double sum = 0.0;
        for (size_t i = 0; i < x.v.size(); ++i) {
            const double mux = mx.v[i], muy = my.v[i];
            const double varx = sxx.v[i] - mux * mux;
            const double vary = syy.v[i] - muy * muy;
            const double cov = sxy.v[i] - mux * muy;
            sum += ((2 * mux * muy + C1) * (2 * cov + C2)) /
                   ((mux * mux + muy * muy + C1) * (varx + vary + C2));
        }
        total += sum / static_cast<double>(x.v.size());
    }
    return total / img1.channels;
}

double VisualQASystem::computeHistogramCorrelation(const Image& img1, const Image& img2) {
    if (img1.channels != img2.channels || img1.empty() || img2.empty()) return 0.0;

    double totalCorr = 0.0;
    for (int c = 0; c < img1.channels; ++c) {
        std::array<double, 256> h1{}, h2{};
        for (size_t i = c; i < img1.data.size(); i += img1.channels) h1[img1.data[i]] += 1.0;
        for (size_t i = c; i < img2.data.size(); i += img2.channels) h2[img2.data[i]] += 1.0;

        // Pearson correlation of the two histograms (OpenCV HISTCMP_CORREL)
        double mean1 = 0, mean2 = 0;
        for (int b = 0; b < 256; ++b) { mean1 += h1[b]; mean2 += h2[b]; }
        mean1 /= 256.0;
        mean2 /= 256.0;
        double num = 0, d1 = 0, d2 = 0;
        for (int b = 0; b < 256; ++b) {
            const double a = h1[b] - mean1, bb = h2[b] - mean2;
            num += a * bb;
            d1 += a * a;
            d2 += bb * bb;
        }
        const double denom = std::sqrt(d1 * d2);
        totalCorr += denom > 0 ? num / denom : 1.0; // two flat histograms are identical
    }

    return totalCorr / img1.channels;
}

std::vector<Point> VisualQASystem::findLargestContour(const Image& img) {
    // Outer boundary pixels of the largest foreground blob (gray > 10)
    std::vector<Point> contour;
    auto region = largestComponent(binaryMask(img, 10), img.width, img.height);
    if (region.empty()) return contour;
    auto inside = [&](int x, int y) {
        return x >= 0 && y >= 0 && x < img.width && y < img.height &&
               region[static_cast<size_t>(y) * img.width + x] != 0;
    };
    for (int y = 0; y < img.height; ++y) {
        for (int x = 0; x < img.width; ++x) {
            if (inside(x, y) && (!inside(x - 1, y) || !inside(x + 1, y) || !inside(x, y - 1) || !inside(x, y + 1))) {
                contour.push_back({x, y});
            }
        }
    }
    return contour;
}

double VisualQASystem::computeShapeDifference(const Image& img1, const Image& img2) {
    if (findLargestContour(img1).empty() || findLargestContour(img2).empty()) {
        return 1.0; // Maximum difference if no contours found
    }

    auto region1 = largestComponent(binaryMask(img1, 10), img1.width, img1.height);
    auto region2 = largestComponent(binaryMask(img2, 10), img2.width, img2.height);
    auto hu1 = huMoments(region1, img1.width, img1.height);
    auto hu2 = huMoments(region2, img2.width, img2.height);

    // cv::matchShapes CONTOURS_MATCH_I1: sum |1/mA - 1/mB|, m = sign(h) * log10|h|
    constexpr double eps = 1e-5;
    double result = 0.0;
    for (int i = 0; i < 7; ++i) {
        const double a = std::abs(hu1[i]), b = std::abs(hu2[i]);
        if (a > eps && b > eps) {
            const double ma = (hu1[i] > 0 ? 1.0 : -1.0) * std::log10(a);
            const double mb = (hu2[i] > 0 ? 1.0 : -1.0) * std::log10(b);
            result += std::abs(1.0 / ma - 1.0 / mb);
        }
    }
    return result;
}

double VisualQASystem::computeColorDistance(const Image& img1, const Image& img2) {
    Image hsv1 = Utils::bgrToHsv(img1);
    Image hsv2 = Utils::bgrToHsv(img2);
    Image diff = Utils::absDiff(hsv1, hsv2);
    if (diff.empty()) return 1.0;

    double sum[3] = {0, 0, 0};
    for (size_t i = 0; i < diff.data.size(); i += 3) {
        sum[0] += diff.data[i];
        sum[1] += diff.data[i + 1];
        sum[2] += diff.data[i + 2];
    }
    const double n = static_cast<double>(diff.pixelCount());
    return (sum[0] / n + sum[1] / n + sum[2] / n) / 3.0 / 255.0;
}

double VisualQASystem::computeEdgeSimilarity(const Image& img1, const Image& img2) {
    Image edges1 = Utils::detectEdges(img1);
    Image edges2 = Utils::detectEdges(img2);
    Image diff = Utils::absDiff(edges1, edges2);
    if (diff.empty()) return 0.0;

    double totalPixels = static_cast<double>(diff.pixelCount());
    double differentPixels = static_cast<double>(std::count_if(diff.data.begin(), diff.data.end(),
                                                               [](uint8_t v) { return v != 0; }));
    return 1.0 - (differentPixels / totalPixels);
}

// Utils implementation
namespace Utils {

Image readImageFile(const fs::path& path) {
    int w = 0, h = 0, n = 0;
    stbi_uc* pixels = stbi_load(path.string().c_str(), &w, &h, &n, 0);
    if (!pixels) return Image();

    // stb gives gray, gray+alpha, RGB or RGBA; convert to gray / BGR / BGRA
    const int outChannels = (n == 2) ? 4 : n;
    Image img(w, h, outChannels);
    for (size_t i = 0, count = img.pixelCount(); i < count; ++i) {
        const stbi_uc* s = pixels + i * n;
        uint8_t* d = img.data.data() + i * outChannels;
        switch (n) {
            case 1: d[0] = s[0]; break;
            case 2: d[0] = d[1] = d[2] = s[0]; d[3] = s[1]; break;
            case 3: d[0] = s[2]; d[1] = s[1]; d[2] = s[0]; break;
            default: d[0] = s[2]; d[1] = s[1]; d[2] = s[0]; d[3] = s[3]; break;
        }
    }
    stbi_image_free(pixels);
    return img;
}

bool writeImageFile(const Image& img, const fs::path& path) {
    if (img.empty()) return false;
    // BGR(A) -> RGB(A) for stb
    std::vector<uint8_t> rgb(img.data);
    if (img.channels >= 3) {
        for (size_t i = 0; i < rgb.size(); i += img.channels) std::swap(rgb[i], rgb[i + 2]);
    }
    const std::string file = path.string();
    std::string ext = getFileExtension(path);
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (ext == ".jpg" || ext == ".jpeg") {
        return stbi_write_jpg(file.c_str(), img.width, img.height, img.channels, rgb.data(), 95) != 0;
    }
    if (ext == ".tga") {
        return stbi_write_tga(file.c_str(), img.width, img.height, img.channels, rgb.data()) != 0;
    }
    if (ext == ".bmp") {
        return stbi_write_bmp(file.c_str(), img.width, img.height, img.channels, rgb.data()) != 0;
    }
    return stbi_write_png(file.c_str(), img.width, img.height, img.channels, rgb.data(),
                          img.width * img.channels) != 0;
}

Image rgbaToBgr(const Image& rgba) {
    Image bgr(rgba.width, rgba.height, 3);
    for (size_t i = 0, n = rgba.pixelCount(); i < n; ++i) {
        const uint8_t* s = rgba.data.data() + i * rgba.channels;
        uint8_t* d = bgr.data.data() + i * 3;
        if (rgba.channels >= 3) { d[0] = s[2]; d[1] = s[1]; d[2] = s[0]; }
        else { d[0] = d[1] = d[2] = s[0]; }
    }
    return bgr;
}

Image bgraToBgr(const Image& bgra) {
    return toBgr(bgra);
}

Image bgrToHsv(const Image& bgr) {
    Image src = toBgr(bgr);
    Image hsv(src.width, src.height, 3);
    for (size_t i = 0, n = src.pixelCount(); i < n; ++i) {
        const double b = src.data[i * 3], g = src.data[i * 3 + 1], r = src.data[i * 3 + 2];
        const double v = std::max({r, g, b});
        const double mn = std::min({r, g, b});
        const double delta = v - mn;
        const double s = v > 0 ? delta / v : 0.0;
        double h = 0.0;
        if (delta > 0) {
            if (v == r) h = 60.0 * (g - b) / delta;
            else if (v == g) h = 120.0 + 60.0 * (b - r) / delta;
            else h = 240.0 + 60.0 * (r - g) / delta;
            if (h < 0) h += 360.0;
        }
        hsv.data[i * 3] = clampByte(h / 2.0);        // OpenCV 8-bit hue range [0,180)
        hsv.data[i * 3 + 1] = clampByte(s * 255.0);
        hsv.data[i * 3 + 2] = clampByte(v);
    }
    return hsv;
}

Image toGray(const Image& img) {
    if (img.channels == 1) return img;
    Image gray(img.width, img.height, 1);
    for (size_t i = 0, n = img.pixelCount(); i < n; ++i) {
        const uint8_t* s = img.data.data() + i * img.channels;
        gray.data[i] = img.channels >= 3 ? clampByte(0.114 * s[0] + 0.587 * s[1] + 0.299 * s[2]) : s[0];
    }
    return gray;
}

Image resize(const Image& img, int width, int height) {
    if (img.empty() || width <= 0 || height <= 0) return Image();
    if (img.width == width && img.height == height) return img;
    Image out(width, height, img.channels);
    const double sx = static_cast<double>(img.width) / width;
    const double sy = static_cast<double>(img.height) / height;
    for (int y = 0; y < height; ++y) {
        const double fy = std::clamp((y + 0.5) * sy - 0.5, 0.0, img.height - 1.0);
        const int y0 = static_cast<int>(fy), y1 = std::min(y0 + 1, img.height - 1);
        const double ty = fy - y0;
        for (int x = 0; x < width; ++x) {
            const double fx = std::clamp((x + 0.5) * sx - 0.5, 0.0, img.width - 1.0);
            const int x0 = static_cast<int>(fx), x1 = std::min(x0 + 1, img.width - 1);
            const double tx = fx - x0;
            for (int c = 0; c < img.channels; ++c) {
                const double top = img.at(x0, y0, c) * (1 - tx) + img.at(x1, y0, c) * tx;
                const double bottom = img.at(x0, y1, c) * (1 - tx) + img.at(x1, y1, c) * tx;
                out.at(x, y, c) = clampByte(top * (1 - ty) + bottom * ty);
            }
        }
    }
    return out;
}

Image normalizeImage(const Image& img) {
    if (img.empty()) return img;
    auto [mnIt, mxIt] = std::minmax_element(img.data.begin(), img.data.end());
    const double mn = *mnIt, mx = *mxIt;
    Image out = img;
    if (mx <= mn) {
        std::fill(out.data.begin(), out.data.end(), static_cast<uint8_t>(0));
        return out;
    }
    const double scale = 255.0 / (mx - mn);
    for (auto& v : out.data) v = clampByte((v - mn) * scale);
    return out;
}

Image applyGaussianBlur(const Image& img, double sigma) {
    if (img.empty() || sigma <= 0.0) return img;
    const int kernelSize = static_cast<int>(sigma * 6 + 1) | 1; // Ensure odd
    const auto k = gaussianKernel(sigma, kernelSize);
    Image out = img;
    for (int c = 0; c < img.channels; ++c) {
        Plane p = gaussianFilter(channelPlane(img, c), k);
        for (int y = 0; y < img.height; ++y)
            for (int x = 0; x < img.width; ++x)
                out.at(x, y, c) = clampByte(p.at(x, y));
    }
    return out;
}

Image detectEdges(const Image& img) {
    // Canny edge detector (Sobel 3x3, L1 gradient, non-maximum suppression, hysteresis 50/150)
    Image gray = toGray(img);
    const int w = gray.width, h = gray.height;
    Image edges(w, h, 1);
    if (w < 3 || h < 3) return edges;

    std::vector<int> gx(static_cast<size_t>(w) * h, 0), gy(gx.size(), 0), mag(gx.size(), 0);
    auto px = [&](int x, int y) { return static_cast<int>(gray.at(std::clamp(x, 0, w - 1), std::clamp(y, 0, h - 1), 0)); };
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            const int dx = (px(x + 1, y - 1) + 2 * px(x + 1, y) + px(x + 1, y + 1)) -
                           (px(x - 1, y - 1) + 2 * px(x - 1, y) + px(x - 1, y + 1));
            const int dy = (px(x - 1, y + 1) + 2 * px(x, y + 1) + px(x + 1, y + 1)) -
                           (px(x - 1, y - 1) + 2 * px(x, y - 1) + px(x + 1, y - 1));
            const size_t i = static_cast<size_t>(y) * w + x;
            gx[i] = dx;
            gy[i] = dy;
            mag[i] = std::abs(dx) + std::abs(dy);
        }
    }

    constexpr int lowThreshold = 50, highThreshold = 150;
    // 0 = none, 1 = weak, 2 = strong
    std::vector<uint8_t> state(gx.size(), 0);
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            const size_t i = static_cast<size_t>(y) * w + x;
            const int m = mag[i];
            if (m <= lowThreshold) continue;
            // quantize gradient direction to 0/45/90/135 degrees
            const double angle = std::atan2(static_cast<double>(gy[i]), static_cast<double>(gx[i])) * 180.0 / 3.14159265358979323846;
            const double a = angle < 0 ? angle + 180.0 : angle;
            int n1, n2;
            if (a < 22.5 || a >= 157.5) { n1 = mag[i - 1]; n2 = mag[i + 1]; }
            else if (a < 67.5) { n1 = mag[i - w + 1]; n2 = mag[i + w - 1]; }
            else if (a < 112.5) { n1 = mag[i - w]; n2 = mag[i + w]; }
            else { n1 = mag[i - w - 1]; n2 = mag[i + w + 1]; }
            if (m >= n1 && m > n2) {
                state[i] = m > highThreshold ? 2 : 1;
            }
        }
    }

    // Hysteresis: keep weak edges connected to strong ones
    std::vector<size_t> stack;
    for (size_t i = 0; i < state.size(); ++i) {
        if (state[i] == 2) {
            edges.data[i] = 255;
            stack.push_back(i);
        }
    }
    while (!stack.empty()) {
        const size_t i = stack.back();
        stack.pop_back();
        const int x = static_cast<int>(i % w), y = static_cast<int>(i / w);
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                const int nx = x + dx, ny = y + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                const size_t n = static_cast<size_t>(ny) * w + nx;
                if (state[n] == 1 && edges.data[n] == 0) {
                    edges.data[n] = 255;
                    stack.push_back(n);
                }
            }
        }
    }
    return edges;
}

Image absDiff(const Image& a, const Image& b) {
    if (a.width != b.width || a.height != b.height || a.channels != b.channels) return Image();
    Image out(a.width, a.height, a.channels);
    for (size_t i = 0; i < a.data.size(); ++i) {
        out.data[i] = static_cast<uint8_t>(std::abs(static_cast<int>(a.data[i]) - static_cast<int>(b.data[i])));
    }
    return out;
}

Image applyJetColorMap(const Image& gray) {
    Image g = toGray(gray);
    Image out(g.width, g.height, 3);
    for (size_t i = 0, n = g.pixelCount(); i < n; ++i) {
        const double v = g.data[i] / 255.0;
        auto ch = [v](double center) { return std::clamp(1.5 - std::abs(4.0 * v - center), 0.0, 1.0); };
        out.data[i * 3] = clampByte(ch(1.0) * 255.0);     // blue
        out.data[i * 3 + 1] = clampByte(ch(2.0) * 255.0); // green
        out.data[i * 3 + 2] = clampByte(ch(3.0) * 255.0); // red
    }
    return out;
}

Image hconcat(const Image& a, const Image& b) {
    if (a.empty()) return b;
    if (b.empty()) return a;
    Image left = a.channels == b.channels ? a : toBgr(a);
    Image right = a.channels == b.channels ? b : toBgr(b);
    if (right.height != left.height) {
        right = resize(right, std::max(1, right.width * left.height / std::max(1, right.height)), left.height);
    }
    Image out(left.width + right.width, left.height, left.channels);
    const size_t lrow = static_cast<size_t>(left.width) * left.channels;
    const size_t rrow = static_cast<size_t>(right.width) * right.channels;
    for (int y = 0; y < out.height; ++y) {
        uint8_t* dst = out.ptr(0, y);
        std::copy_n(left.ptr(0, y), lrow, dst);
        std::copy_n(right.ptr(0, y), rrow, dst + lrow);
    }
    return out;
}

bool ensureDirectory(const fs::path& path) {
    if (path.empty()) return true;
    std::error_code ec;
    if (fs::exists(path, ec)) return true;
    fs::create_directories(path, ec);
    return !ec && fs::exists(path, ec);
}

std::string getFileExtension(const fs::path& path) {
    return path.extension().string();
}

bool isValidImageFile(const fs::path& path) {
    std::string ext = getFileExtension(path);
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".tga" || ext == ".bmp";
}

std::string formatScore(double score, int precision) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(precision) << score;
    return oss.str();
}

std::string getStatusEmoji(bool passed) {
    return passed ? "\xE2\x9C\x85" : "\xE2\x9D\x8C"; // U+2705 / U+274C (UTF-8)
}

std::string generateTimestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tmBuf{};
#ifdef _WIN32
    localtime_s(&tmBuf, &t);
#else
    localtime_r(&t, &tmBuf);
#endif
    std::stringstream ss;
    ss << std::put_time(&tmBuf, "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

} // namespace Utils

} // namespace VisualQA
} // namespace MagiTech
