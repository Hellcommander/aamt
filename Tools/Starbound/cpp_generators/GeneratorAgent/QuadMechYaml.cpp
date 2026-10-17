#include "QuadMechYaml.hpp"

#include <cctype>
#include <charconv>
#include <cstdint>
#include <vector>

namespace MagiTech {
namespace QuadMech {

namespace {

using ojson = nlohmann::ordered_json;

struct YamlLine {
    size_t number = 0;   // 1-based source line
    size_t indent = 0;   // leading spaces
    std::string text;    // content without indentation, comment or trailing spaces
};

bool isSpace(char c) { return c == ' ' || c == '\t'; }

std::string trim(const std::string& s) {
    size_t b = 0, e = s.size();
    while (b < e && isSpace(s[b])) ++b;
    while (e > b && isSpace(s[e - 1])) --e;
    return s.substr(b, e - b);
}

// A quote only opens a quoted scalar at the start of a token.
bool quoteCanOpen(const std::string& s, size_t i) {
    if (i == 0) return true;
    const char p = s[i - 1];
    return isSpace(p) || p == '[' || p == '{' || p == ',' || p == ':' || p == '-';
}

// Removes a "# comment" ('#' at line start or after whitespace, outside quotes).
std::string stripComment(const std::string& s) {
    char quote = 0;
    for (size_t i = 0; i < s.size(); ++i) {
        const char c = s[i];
        if (quote) {
            if (quote == '"' && c == '\\') { ++i; continue; }
            if (c == quote) {
                if (quote == '\'' && i + 1 < s.size() && s[i + 1] == '\'') { ++i; continue; }
                quote = 0;
            }
            continue;
        }
        if ((c == '"' || c == '\'') && quoteCanOpen(s, i)) { quote = c; continue; }
        if (c == '#' && (i == 0 || isSpace(s[i - 1]))) return s.substr(0, i);
    }
    return s;
}

ojson plainScalar(const std::string& raw) {
    const std::string s = trim(raw);
    if (s.empty() || s == "~" || s == "null" || s == "Null" || s == "NULL") return nullptr;
    if (s == "true" || s == "True" || s == "TRUE") return true;
    if (s == "false" || s == "False" || s == "FALSE") return false;

    const char* first = s.data();
    const char* last = s.data() + s.size();
    const char* numFirst = (*first == '+') ? first + 1 : first;

    int64_t asInt = 0;
    if (auto [p, ec] = std::from_chars(numFirst, last, asInt); ec == std::errc() && p == last) return asInt;

    double asDouble = 0.0;
    if (auto [p, ec] = std::from_chars(numFirst, last, asDouble); ec == std::errc() && p == last) return asDouble;

    return s;
}

class YamlParser {
public:
    explicit YamlParser(const std::string& text) { splitLines(text); }

    ojson parseDocument() {
        if (m_lines.empty()) return ojson();
        ojson root = parseBlock(m_lines[0].indent);
        if (m_pos < m_lines.size()) fail("unexpected content", m_lines[m_pos].number);
        return root;
    }

private:
    std::vector<YamlLine> m_lines;
    size_t m_pos = 0;

    [[noreturn]] static void fail(const std::string& message, size_t line) {
        throw QuadMechYamlError(message, line);
    }

    void splitLines(const std::string& text) {
        bool seenContent = false;
        size_t lineNo = 0;
        size_t start = 0;
        while (start <= text.size()) {
            size_t end = text.find('\n', start);
            if (end == std::string::npos) end = text.size();
            std::string raw = text.substr(start, end - start);
            start = end + 1;
            ++lineNo;
            if (!raw.empty() && raw.back() == '\r') raw.pop_back();

            std::string content = stripComment(raw);
            while (!content.empty() && isSpace(content.back())) content.pop_back();
            if (trim(content).empty()) {
                if (end == text.size()) break;
                continue;
            }

            size_t indent = 0;
            while (indent < content.size() && isSpace(content[indent])) {
                if (content[indent] == '\t') fail("tabs are not allowed in indentation", lineNo);
                ++indent;
            }
            std::string body = content.substr(indent);

            if (indent == 0 && (body == "---" || body == "...")) {
                if (seenContent && body == "---") fail("multiple documents are not supported", lineNo);
                if (end == text.size()) break;
                continue;
            }

            seenContent = true;
            m_lines.push_back({lineNo, indent, std::move(body)});
            if (end == text.size()) break;
        }
    }

    static bool isSeqItem(const std::string& t) {
        return t == "-" || (t.size() >= 2 && t[0] == '-' && t[1] == ' ');
    }

    // Index of the ':' separating a block-mapping key from its value, or npos.
    static size_t findMappingColon(const std::string& t) {
        if (t.empty() || t[0] == '[' || t[0] == '{') return std::string::npos;
        size_t i = 0;
        if (t[0] == '"' || t[0] == '\'') {
            const char q = t[0];
            for (i = 1; i < t.size(); ++i) {
                if (q == '"' && t[i] == '\\') { ++i; continue; }
                if (t[i] == q) {
                    if (q == '\'' && i + 1 < t.size() && t[i + 1] == '\'') { ++i; continue; }
                    break;
                }
            }
            if (i >= t.size()) return std::string::npos;
            ++i;
        }
        for (; i < t.size(); ++i) {
            if (t[i] == ':' && (i + 1 == t.size() || isSpace(t[i + 1]))) return i;
        }
        return std::string::npos;
    }

    static std::string parseQuoted(const std::string& s, size_t& i, size_t line) {
        const char q = s[i++];
        std::string out;
        while (i < s.size()) {
            const char c = s[i++];
            if (c == q) {
                if (q == '\'' && i < s.size() && s[i] == '\'') { out += '\''; ++i; continue; }
                return out;
            }
            if (q == '"' && c == '\\') {
                if (i >= s.size()) break;
                const char e = s[i++];
                switch (e) {
                    case 'n': out += '\n'; break;
                    case 't': out += '\t'; break;
                    case 'r': out += '\r'; break;
                    case '0': out += '\0'; break;
                    case 'b': out += '\b'; break;
                    case 'f': out += '\f'; break;
                    case '"': out += '"'; break;
                    case '\\': out += '\\'; break;
                    case '/': out += '/'; break;
                    case ' ': out += ' '; break;
                    case 'x':
                    case 'u': {
                        const size_t digits = (e == 'x') ? 2 : 4;
                        if (i + digits > s.size()) fail("truncated escape sequence", line);
                        unsigned code = 0;
                        auto [p, ec] = std::from_chars(s.data() + i, s.data() + i + digits, code, 16);
                        if (ec != std::errc() || p != s.data() + i + digits) fail("invalid escape sequence", line);
                        i += digits;
                        // UTF-8 encode the code point (BMP only).
                        if (code < 0x80) {
                            out += static_cast<char>(code);
                        } else if (code < 0x800) {
                            out += static_cast<char>(0xC0 | (code >> 6));
                            out += static_cast<char>(0x80 | (code & 0x3F));
                        } else {
                            out += static_cast<char>(0xE0 | (code >> 12));
                            out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
                            out += static_cast<char>(0x80 | (code & 0x3F));
                        }
                        break;
                    }
                    default: fail(std::string("unknown escape sequence \\") + e, line);
                }
                continue;
            }
            out += c;
        }
        fail("unterminated quoted string", line);
    }

    static void skipWs(const std::string& s, size_t& i) {
        while (i < s.size() && isSpace(s[i])) ++i;
    }

    static ojson parseFlowValue(const std::string& s, size_t& i, size_t line, char closer) {
        skipWs(s, i);
        if (i >= s.size()) fail("unexpected end of flow collection", line);
        if (s[i] == '[' || s[i] == '{') return parseFlow(s, i, line);
        if (s[i] == '"' || s[i] == '\'') return parseQuoted(s, i, line);
        const size_t start = i;
        while (i < s.size() && s[i] != ',' && s[i] != closer) ++i;
        return plainScalar(s.substr(start, i - start));
    }

    static ojson parseFlow(const std::string& s, size_t& i, size_t line) {
        const char open = s[i++];
        const char closer = (open == '[') ? ']' : '}';
        ojson result = (open == '[') ? ojson::array() : ojson::object();
        skipWs(s, i);
        if (i < s.size() && s[i] == closer) { ++i; return result; }
        while (true) {
            if (open == '[') {
                result.push_back(parseFlowValue(s, i, line, closer));
            } else {
                skipWs(s, i);
                std::string key;
                if (i < s.size() && (s[i] == '"' || s[i] == '\'')) {
                    key = parseQuoted(s, i, line);
                    skipWs(s, i);
                } else {
                    const size_t start = i;
                    while (i < s.size() && s[i] != ':' && s[i] != ',' && s[i] != closer) ++i;
                    key = trim(s.substr(start, i - start));
                }
                if (i >= s.size() || s[i] != ':') fail("expected ':' in flow mapping", line);
                ++i;
                result[key] = parseFlowValue(s, i, line, closer);
            }
            skipWs(s, i);
            if (i >= s.size()) fail("unterminated flow collection", line);
            if (s[i] == ',') { ++i; continue; }
            if (s[i] == closer) { ++i; return result; }
            fail(std::string("unexpected character '") + s[i] + "' in flow collection", line);
        }
    }

    static bool flowBalanced(const std::string& s) {
        int depth = 0;
        char quote = 0;
        for (size_t i = 0; i < s.size(); ++i) {
            const char c = s[i];
            if (quote) {
                if (quote == '"' && c == '\\') { ++i; continue; }
                if (c == quote) quote = 0;
                continue;
            }
            if ((c == '"' || c == '\'') && quoteCanOpen(s, i)) quote = c;
            else if (c == '[' || c == '{') ++depth;
            else if (c == ']' || c == '}') --depth;
        }
        return depth <= 0 && quote == 0;
    }

    // Parses an inline value starting on the current line; consumes that line
    // and, for flow collections, any continuation lines.
    ojson parseValueText(std::string text) {
        const size_t line = m_lines[m_pos].number;
        ++m_pos;
        const char c = text[0];
        if (c == '|' || c == '>') fail("block scalars are not supported", line);
        if (c == '&' || c == '*' || c == '!') fail("anchors, aliases and tags are not supported", line);

        if (c == '[' || c == '{') {
            while (!flowBalanced(text)) {
                if (m_pos >= m_lines.size()) fail("unterminated flow collection", line);
                text += ' ';
                text += m_lines[m_pos].text;
                ++m_pos;
            }
            size_t i = 0;
            ojson v = parseFlow(text, i, line);
            skipWs(text, i);
            if (i != text.size()) fail("unexpected characters after flow collection", line);
            return v;
        }
        if (c == '"' || c == '\'') {
            size_t i = 0;
            std::string s = parseQuoted(text, i, line);
            skipWs(text, i);
            if (i != text.size()) fail("unexpected characters after quoted string", line);
            return s;
        }
        return plainScalar(text);
    }

    ojson parseBlock(size_t indent) {
        if (isSeqItem(m_lines[m_pos].text)) return parseSequence(indent);
        return parseMapping(indent);
    }

    ojson parseSequence(size_t indent) {
        ojson arr = ojson::array();
        while (m_pos < m_lines.size() && m_lines[m_pos].indent == indent && isSeqItem(m_lines[m_pos].text)) {
            YamlLine& l = m_lines[m_pos];
            size_t offset = 1;
            while (offset < l.text.size() && isSpace(l.text[offset])) ++offset;
            const std::string rest = l.text.substr(offset);

            if (rest.empty()) {
                ++m_pos;
                if (m_pos < m_lines.size() && m_lines[m_pos].indent > indent)
                    arr.push_back(parseBlock(m_lines[m_pos].indent));
                else
                    arr.push_back(nullptr);
            } else if (isSeqItem(rest) || findMappingColon(rest) != std::string::npos) {
                // "- key: value" / "- - item": the nested block continues on the
                // following lines at the column where its first entry starts.
                l.indent = indent + offset;
                l.text = rest;
                arr.push_back(parseBlock(l.indent));
            } else {
                arr.push_back(parseValueText(rest));
            }
        }
        if (m_pos < m_lines.size() && m_lines[m_pos].indent > indent)
            fail("unexpected indentation", m_lines[m_pos].number);
        return arr;
    }

    static std::string parseKey(const std::string& rawKey, size_t line) {
        const std::string k = trim(rawKey);
        if (!k.empty() && (k[0] == '"' || k[0] == '\'')) {
            size_t i = 0;
            std::string out = parseQuoted(k, i, line);
            if (i != k.size()) fail("unexpected characters after quoted key", line);
            return out;
        }
        if (k.empty()) fail("empty mapping key", line);
        return k;
    }

    ojson parseMapping(size_t indent) {
        ojson obj = ojson::object();
        while (m_pos < m_lines.size() && m_lines[m_pos].indent == indent && !isSeqItem(m_lines[m_pos].text)) {
            const YamlLine& l = m_lines[m_pos];
            const size_t colon = findMappingColon(l.text);
            if (colon == std::string::npos) {
                // A lone scalar (or flow collection) is a valid block value.
                if (obj.empty()) return parseValueText(l.text);
                fail("expected 'key: value'", l.number);
            }
            const size_t line = l.number;
            const std::string key = parseKey(l.text.substr(0, colon), line);
            const std::string rest = trim(l.text.substr(colon + 1));
            if (obj.contains(key)) fail("duplicate key '" + key + "'", line);

            if (rest.empty()) {
                ++m_pos;
                if (m_pos < m_lines.size() &&
                    (m_lines[m_pos].indent > indent ||
                     (m_lines[m_pos].indent == indent && isSeqItem(m_lines[m_pos].text)))) {
                    obj[key] = parseBlock(m_lines[m_pos].indent);
                } else {
                    obj[key] = nullptr;
                }
            } else {
                obj[key] = parseValueText(rest);
            }
        }
        if (m_pos < m_lines.size() && m_lines[m_pos].indent > indent)
            fail("unexpected indentation", m_lines[m_pos].number);
        return obj;
    }
};

} // namespace

nlohmann::ordered_json parseQuadMechYaml(const std::string& text) {
    const size_t first = text.find_first_not_of(" \t\r\n");
    if (first != std::string::npos && text[first] == '{') {
        // JSON is (almost) a YAML subset; prefer the full JSON parser for it.
        ojson asJson = ojson::parse(text, nullptr, false, true);
        if (!asJson.is_discarded()) return asJson;
    }
    YamlParser parser(text);
    return parser.parseDocument();
}

} // namespace QuadMech
} // namespace MagiTech
