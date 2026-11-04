#include "OllamaClient.hpp"
#include <sstream>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <algorithm>
#include <optional>
#include <vector>

#ifdef _WIN32
    #ifndef NOMINMAX
        #define NOMINMAX
    #endif
    #include <windows.h>
    #include <winhttp.h>
    #pragma comment(lib, "winhttp.lib")
#else
    #include <curl/curl.h>
#endif

namespace MagiTech {
namespace GeneratorAgent {

OllamaClient::OllamaClient() : m_config() {}

OllamaClient::OllamaClient(const Config& config) : m_config(config) {}

OllamaClient::~OllamaClient() = default;

void OllamaClient::setConfig(const Config& config) {
    m_config = config;
}

bool OllamaClient::checkConnection() const {
    if (!m_config.enabled) {
        return false;
    }
    
    try {
        return httpGet(m_config.url + "/api/tags");
    } catch (...) {
        return false;
    }
}

bool OllamaClient::isAvailable() const {
    return checkConnection();
}

std::optional<OllamaClient::EnhancedDescription> OllamaClient::enhanceDescription(
    const std::string& description
) const {
    if (!m_config.enabled || description.empty()) {
        return std::nullopt;
    }

    if (!isAvailable()) {
        return std::nullopt;
    }

    try {
        std::stringstream prompt;
        prompt << "You are a game asset designer for Starbound. Enhance this asset description to provide detailed visual guidance for procedural generation:\n\n";
        prompt << "Original description: " << description << "\n\n";
        prompt << "Provide an enhanced description that includes:\n";
        prompt << "- Specific color palette suggestions (RGB values)\n";
        prompt << "- Visual style details (pixel art, shading, outlines)\n";
        prompt << "- Material/texture characteristics\n";
        prompt << "- Size and proportion details\n";
        prompt << "- Any thematic elements that should be emphasized\n\n";
        prompt << "Return ONLY the enhanced description, no other text.";

        nlohmann::json requestBody = {
            {"model", m_config.model},
            {"prompt", prompt.str()},
            {"stream", false}
        };

        auto response = makeRequest("/api/generate", requestBody);
        if (!response) {
            return std::nullopt;
        }

        if (response->contains("response")) {
            std::string enhanced = response->at("response").get<std::string>();
            // Trim whitespace
            enhanced.erase(0, enhanced.find_first_not_of(" \t\n\r"));
            enhanced.erase(enhanced.find_last_not_of(" \t\n\r") + 1);

            EnhancedDescription result;
            result.original = description;
            result.enhanced = enhanced;
            result.wasEnhanced = (enhanced != description && enhanced.length() > description.length());

            return result;
        }
    } catch (const std::exception& e) {
        std::cerr << "OllamaClient::enhanceDescription error: " << e.what() << std::endl;
    }

    return std::nullopt;
}

std::optional<OllamaClient::ExtractedParameters> OllamaClient::extractParameters(
    const std::string& description
) const {
    if (!m_config.enabled || description.empty()) {
        return std::nullopt;
    }

    if (!isAvailable()) {
        return std::nullopt;
    }

    try {
        std::stringstream prompt;
        prompt << "Extract visual parameters from this description as JSON:\n";
        prompt << "\"" << description << "\"\n\n";
        prompt << "Return ONLY a JSON object with: colorPalette (array of RGB arrays like [[r,g,b],...]), style (string), hasGradient (bool), hasPattern (bool), hasSparkles (bool)";

        nlohmann::json requestBody = {
            {"model", m_config.model},
            {"prompt", prompt.str()},
            {"stream", false}
        };

        auto response = makeRequest("/api/generate", requestBody);
        if (!response) {
            return std::nullopt;
        }

        if (response->contains("response")) {
            std::string jsonStr = response->at("response").get<std::string>();
            
            // Try to extract JSON from response
            size_t jsonStart = jsonStr.find('{');
            size_t jsonEnd = jsonStr.rfind('}');
            
            if (jsonStart != std::string::npos && jsonEnd != std::string::npos && jsonEnd > jsonStart) {
                jsonStr = jsonStr.substr(jsonStart, jsonEnd - jsonStart + 1);
                try {
                    nlohmann::json json = nlohmann::json::parse(jsonStr);
                    return parseExtractedParameters(json);
                } catch (...) {
                    // JSON parsing failed, try fallback
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "OllamaClient::extractParameters error: " << e.what() << std::endl;
    }

    return std::nullopt;
}

std::optional<OllamaClient::EnhancementResult> OllamaClient::enhance(
    const std::string& description
) const {
    EnhancementResult result;
    
    auto enhancedDesc = enhanceDescription(description);
    if (enhancedDesc) {
        result.description = *enhancedDesc;
    } else {
        result.description.original = description;
        result.description.enhanced = description;
        result.description.wasEnhanced = false;
    }

    auto params = extractParameters(result.description.enhanced);
    if (params) {
        result.parameters = *params;
    }

    return result;
}

std::optional<nlohmann::json> OllamaClient::makeRequest(
    const std::string& endpoint,
    const nlohmann::json& body
) const {
    try {
        std::string url = m_config.url + endpoint;
        std::string bodyStr = body.dump();
        
        std::string response = httpPost(url, bodyStr);
        if (response.empty()) {
            return std::nullopt;
        }

        return nlohmann::json::parse(response);
    } catch (const std::exception& e) {
        std::cerr << "OllamaClient::makeRequest error: " << e.what() << std::endl;
        return std::nullopt;
    }
}

OllamaClient::ExtractedParameters OllamaClient::parseExtractedParameters(
    const nlohmann::json& json
) const {
    ExtractedParameters params;

    if (json.contains("colorPalette") && json["colorPalette"].is_array()) {
        for (const auto& color : json["colorPalette"]) {
            if (color.is_array() && color.size() >= 3) {
                params.colorPalette.push_back({
                    color[0].get<int>(),
                    color[1].get<int>(),
                    color[2].get<int>()
                });
            }
        }
    }

    if (json.contains("style") && json["style"].is_string()) {
        params.style = json["style"].get<std::string>();
    }

    if (json.contains("hasGradient") && json["hasGradient"].is_boolean()) {
        params.hasGradient = json["hasGradient"].get<bool>();
    }

    if (json.contains("hasPattern") && json["hasPattern"].is_boolean()) {
        params.hasPattern = json["hasPattern"].get<bool>();
    }

    if (json.contains("hasSparkles") && json["hasSparkles"].is_boolean()) {
        params.hasSparkles = json["hasSparkles"].get<bool>();
    }

    return params;
}

#ifdef _WIN32
// Windows implementation using WinHTTP (wide-character API only)
namespace {

std::wstring widen(const std::string& s) {
    if (s.empty()) return {};
    const int len = MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), nullptr, 0);
    std::wstring out(static_cast<size_t>(len), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), out.data(), len);
    return out;
}

// Closes a WinHTTP handle when it goes out of scope
struct WinHttpHandle {
    HINTERNET handle = nullptr;
    WinHttpHandle() = default;
    explicit WinHttpHandle(HINTERNET h) : handle(h) {}
    WinHttpHandle(const WinHttpHandle&) = delete;
    WinHttpHandle& operator=(const WinHttpHandle&) = delete;
    ~WinHttpHandle() { if (handle) WinHttpCloseHandle(handle); }
    explicit operator bool() const { return handle != nullptr; }
};

struct ParsedUrl {
    std::wstring host;
    std::wstring path;
    INTERNET_PORT port = 80;
    bool secure = false;
};

std::optional<ParsedUrl> crackUrl(const std::string& url) {
    std::wstring wUrl = widen(url);
    URL_COMPONENTS comp{};
    comp.dwStructSize = sizeof(comp);
    comp.dwSchemeLength = static_cast<DWORD>(-1);
    comp.dwHostNameLength = static_cast<DWORD>(-1);
    comp.dwUrlPathLength = static_cast<DWORD>(-1);
    comp.dwExtraInfoLength = static_cast<DWORD>(-1);
    if (!WinHttpCrackUrl(wUrl.c_str(), static_cast<DWORD>(wUrl.size()), 0, &comp)) {
        return std::nullopt;
    }
    ParsedUrl parsed;
    parsed.host.assign(comp.lpszHostName, comp.dwHostNameLength);
    parsed.path.assign(comp.lpszUrlPath, comp.dwUrlPathLength);
    if (comp.lpszExtraInfo && comp.dwExtraInfoLength > 0) {
        parsed.path.append(comp.lpszExtraInfo, comp.dwExtraInfoLength);
    }
    if (parsed.path.empty()) parsed.path = L"/";
    parsed.secure = comp.nScheme == INTERNET_SCHEME_HTTPS;
    parsed.port = comp.nPort != 0 ? comp.nPort
                                  : static_cast<INTERNET_PORT>(parsed.secure ? INTERNET_DEFAULT_HTTPS_PORT
                                                                             : INTERNET_DEFAULT_HTTP_PORT);
    return parsed;
}

// Opens session/connection/request for `verb` on `url` with the configured timeout
bool openRequest(const std::string& url, const wchar_t* verb, int timeoutSeconds,
                 WinHttpHandle& session, WinHttpHandle& connect, WinHttpHandle& request) {
    auto parsed = crackUrl(url);
    if (!parsed) return false;

    session.handle = WinHttpOpen(L"OllamaClient/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                 WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) return false;

    const int timeoutMs = std::max(1, timeoutSeconds) * 1000;
    WinHttpSetTimeouts(session.handle, timeoutMs, timeoutMs, timeoutMs, timeoutMs);

    connect.handle = WinHttpConnect(session.handle, parsed->host.c_str(), parsed->port, 0);
    if (!connect) return false;

    request.handle = WinHttpOpenRequest(connect.handle, verb, parsed->path.c_str(), nullptr,
                                        WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                        parsed->secure ? WINHTTP_FLAG_SECURE : 0);
    return static_cast<bool>(request);
}

DWORD statusCode(HINTERNET request) {
    DWORD code = 0;
    DWORD size = sizeof(code);
    if (!WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &code, &size, WINHTTP_NO_HEADER_INDEX)) {
        return 0;
    }
    return code;
}

} // namespace

std::string OllamaClient::httpPost(const std::string& url, const std::string& body) const {
    WinHttpHandle session, connect, request;
    if (!openRequest(url, L"POST", m_config.timeoutSeconds, session, connect, request)) {
        return "";
    }

    static const wchar_t kHeaders[] = L"Content-Type: application/json\r\n";
    if (!WinHttpAddRequestHeaders(request.handle, kHeaders, static_cast<DWORD>(-1), WINHTTP_ADDREQ_FLAG_ADD)) {
        return "";
    }

    if (!WinHttpSendRequest(request.handle, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
                            static_cast<DWORD>(body.size()), 0)) {
        return "";
    }

    if (!WinHttpReceiveResponse(request.handle, nullptr)) {
        return "";
    }

    const DWORD code = statusCode(request.handle);
    if (code < 200 || code >= 300) {
        std::cerr << "OllamaClient::httpPost: HTTP " << code << " from " << url << std::endl;
        return "";
    }

    // Read response
    std::string response;
    for (;;) {
        DWORD bytesAvailable = 0;
        if (!WinHttpQueryDataAvailable(request.handle, &bytesAvailable) || bytesAvailable == 0) {
            break;
        }
        std::vector<char> buffer(bytesAvailable);
        DWORD bytesRead = 0;
        if (!WinHttpReadData(request.handle, buffer.data(), bytesAvailable, &bytesRead) || bytesRead == 0) {
            break;
        }
        response.append(buffer.data(), bytesRead);
    }
    return response;
}

bool OllamaClient::httpGet(const std::string& url) const {
    WinHttpHandle session, connect, request;
    if (!openRequest(url, L"GET", m_config.timeoutSeconds, session, connect, request)) {
        return false;
    }

    if (!WinHttpSendRequest(request.handle, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        return false;
    }

    if (!WinHttpReceiveResponse(request.handle, nullptr)) {
        return false;
    }

    const DWORD code = statusCode(request.handle);
    return code >= 200 && code < 300;
}
#else
// Linux/Mac implementation using libcurl
std::string OllamaClient::httpPost(const std::string& url, const std::string& body) const {
    CURL* curl = curl_easy_init();
    if (!curl) {
        return "";
    }
    
    std::string response;
    
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
    // curl_easy_setopt is variadic: pass a real function pointer, not a lambda object
    using WriteCallback = size_t (*)(char*, size_t, size_t, void*);
    WriteCallback writeCallback = [](char* contents, size_t size, size_t nmemb, void* userdata) -> size_t {
        const size_t totalSize = size * nmemb;
        static_cast<std::string*>(userdata)->append(contents, totalSize);
        return totalSize;
    };
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, static_cast<long>(m_config.timeoutSeconds));
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    CURLcode res = curl_easy_perform(curl);
    
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK) {
        return "";
    }
    
    return response;
}

bool OllamaClient::httpGet(const std::string& url) const {
    CURL* curl = curl_easy_init();
    if (!curl) {
        return false;
    }
    
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_NOBODY, 1L);
    
    CURLcode res = curl_easy_perform(curl);
    long responseCode = 0;
    if (res == CURLE_OK) {
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &responseCode);
    }
    
    curl_easy_cleanup(curl);
    
    return (res == CURLE_OK && responseCode >= 200 && responseCode < 300);
}
#endif

} // namespace GeneratorAgent
} // namespace MagiTech
