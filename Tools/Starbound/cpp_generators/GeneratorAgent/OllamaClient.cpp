#include "OllamaClient.hpp"
#include <sstream>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>

#ifdef _WIN32
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
// Windows implementation using WinHTTP
std::string OllamaClient::httpPost(const std::string& url, const std::string& body) const {
    HINTERNET hSession = nullptr;
    HINTERNET hConnect = nullptr;
    HINTERNET hRequest = nullptr;
    
    try {
        // Parse URL
        URL_COMPONENTSA urlComp;
        ZeroMemory(&urlComp, sizeof(urlComp));
        urlComp.dwStructSize = sizeof(urlComp);
        urlComp.dwSchemeLength = -1;
        urlComp.dwHostNameLength = -1;
        urlComp.dwUrlPathLength = -1;
        
        std::vector<char> urlBuf(url.begin(), url.end());
        urlBuf.push_back('\0');
        
        if (!WinHttpCrackUrlA(urlBuf.data(), urlBuf.size() - 1, 0, &urlComp)) {
            return "";
        }
        
        std::string host(urlComp.lpszHostName, urlComp.dwHostNameLength);
        std::string path(urlComp.lpszUrlPath, urlComp.dwUrlPathLength);
        if (urlComp.lpszExtraInfo) {
            path += std::string(urlComp.lpszExtraInfo, urlComp.dwExtraInfoLength);
        }
        
        int port = (urlComp.nScheme == INTERNET_SCHEME_HTTPS) ? 443 : 80;
        if (urlComp.nPort != 0) {
            port = urlComp.nPort;
        }
        
        // Open session
        hSession = WinHttpOpen(L"OllamaClient/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                               WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
        if (!hSession) {
            return "";
        }
        
        // Connect
        std::wstring wHost(host.begin(), host.end());
        hConnect = WinHttpConnect(hSession, wHost.c_str(), port, 0);
        if (!hConnect) {
            WinHttpCloseHandle(hSession);
            return "";
        }
        
        // Open request
        std::wstring wPath(path.begin(), path.end());
        hRequest = WinHttpOpenRequest(hConnect, L"POST", wPath.c_str(), nullptr,
                                      WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                      (urlComp.nScheme == INTERNET_SCHEME_HTTPS) ? WINHTTP_FLAG_SECURE : 0);
        if (!hRequest) {
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return "";
        }
        
        // Set headers
        std::string headers = "Content-Type: application/json\r\n";
        std::wstring wHeaders(headers.begin(), headers.end());
        
        if (!WinHttpAddRequestHeaders(hRequest, wHeaders.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD)) {
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return "";
        }
        
        // Send request
        std::vector<BYTE> bodyData(body.begin(), body.end());
        if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                bodyData.data(), bodyData.size(), bodyData.size(), 0)) {
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return "";
        }
        
        // Receive response
        if (!WinHttpReceiveResponse(hRequest, nullptr)) {
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return "";
        }
        
        // Read response
        std::string response;
        DWORD bytesAvailable = 0;
        DWORD bytesRead = 0;
        
        do {
            if (!WinHttpQueryDataAvailable(hRequest, &bytesAvailable)) {
                break;
            }
            
            if (bytesAvailable == 0) {
                break;
            }
            
            std::vector<char> buffer(bytesAvailable);
            if (!WinHttpReadData(hRequest, buffer.data(), bytesAvailable, &bytesRead)) {
                break;
            }
            
            response.append(buffer.data(), bytesRead);
        } while (bytesRead > 0);
        
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        
        return response;
    } catch (...) {
        if (hRequest) WinHttpCloseHandle(hRequest);
        if (hConnect) WinHttpCloseHandle(hConnect);
        if (hSession) WinHttpCloseHandle(hSession);
        return "";
    }
}

bool OllamaClient::httpGet(const std::string& url) const {
    HINTERNET hSession = nullptr;
    HINTERNET hConnect = nullptr;
    HINTERNET hRequest = nullptr;
    
    try {
        // Parse URL (similar to httpPost)
        URL_COMPONENTSA urlComp;
        ZeroMemory(&urlComp, sizeof(urlComp));
        urlComp.dwStructSize = sizeof(urlComp);
        urlComp.dwSchemeLength = -1;
        urlComp.dwHostNameLength = -1;
        urlComp.dwUrlPathLength = -1;
        
        std::vector<char> urlBuf(url.begin(), url.end());
        urlBuf.push_back('\0');
        
        if (!WinHttpCrackUrlA(urlBuf.data(), urlBuf.size() - 1, 0, &urlComp)) {
            return false;
        }
        
        std::string host(urlComp.lpszHostName, urlComp.dwHostNameLength);
        std::string path(urlComp.lpszUrlPath, urlComp.dwUrlPathLength);
        if (urlComp.lpszExtraInfo) {
            path += std::string(urlComp.lpszExtraInfo, urlComp.dwExtraInfoLength);
        }
        
        int port = (urlComp.nScheme == INTERNET_SCHEME_HTTPS) ? 443 : 80;
        if (urlComp.nPort != 0) {
            port = urlComp.nPort;
        }
        
        hSession = WinHttpOpen(L"OllamaClient/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                               WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
        if (!hSession) {
            return false;
        }
        
        std::wstring wHost(host.begin(), host.end());
        hConnect = WinHttpConnect(hSession, wHost.c_str(), port, 0);
        if (!hConnect) {
            WinHttpCloseHandle(hSession);
            return false;
        }
        
        std::wstring wPath(path.begin(), path.end());
        hRequest = WinHttpOpenRequest(hConnect, L"GET", wPath.c_str(), nullptr,
                                      WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                      (urlComp.nScheme == INTERNET_SCHEME_HTTPS) ? WINHTTP_FLAG_SECURE : 0);
        if (!hRequest) {
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return false;
        }
        
        if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return false;
        }
        
        if (!WinHttpReceiveResponse(hRequest, nullptr)) {
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return false;
        }
        
        DWORD statusCode = 0;
        DWORD statusCodeSize = sizeof(statusCode);
        if (WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                                 WINHTTP_HEADER_NAME_BY_INDEX, &statusCode, &statusCodeSize,
                                 WINHTTP_NO_HEADER_INDEX)) {
            bool success = (statusCode >= 200 && statusCode < 300);
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);
            WinHttpCloseHandle(hSession);
            return success;
        }
        
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return false;
    } catch (...) {
        if (hRequest) WinHttpCloseHandle(hRequest);
        if (hConnect) WinHttpCloseHandle(hConnect);
        if (hSession) WinHttpCloseHandle(hSession);
        return false;
    }
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
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, [](void* contents, size_t size, size_t nmemb, std::string* data) {
        size_t totalSize = size * nmemb;
        data->append((char*)contents, totalSize);
        return totalSize;
    });
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
