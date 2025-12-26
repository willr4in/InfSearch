#include "tokenizer.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cctype>

Tokenizer::Tokenizer(const std::string &stopwords_path): stopwords_path(stopwords_path) {
    load_stopwords();
}

Tokenizer::~Tokenizer() {}

void Tokenizer::load_stopwords() {
    stopwords.clear();
    std::ifstream f(stopwords_path);
    std::string line;
    while (std::getline(f, line)) {
        // trim whitespace
        while (!line.empty() && std::isspace(static_cast<unsigned char>(line.back()))) line.pop_back();
        size_t i = 0; while (i < line.size() && std::isspace(static_cast<unsigned char>(line[i]))) i++; if (i>0) line = line.substr(i);
        if (line.empty()) continue;
        // lowercase ASCII part
        std::string s = line;
        std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::tolower(c); });
        stopwords.push_back(s);
    }
}

bool Tokenizer::is_stopword(const std::string &w) {
    for (const auto &s : stopwords) if (s == w) return true;
    return false;
}

std::vector<std::string> Tokenizer::tokenize(const std::string &text) {
    std::vector<std::string> out;
    std::string cur;
    for (size_t i = 0; i < text.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(text[i]);
        bool is_letter = false;
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) is_letter = true;
        else if (c >= 0x80) is_letter = true; // part of UTF-8 multibyte; treat as letter
        if (is_letter) {
            // for ASCII letters, lowercase
            if (c < 128) cur.push_back(std::tolower(c));
            else cur.push_back(text[i]);
        } else {
            if (!cur.empty()) {
                // normalize ascii lowercase already; for non-ascii we keep as-is
                if (!is_stopword(cur)) out.push_back(cur);
                cur.clear();
            }
        }
    }
    if (!cur.empty() && !is_stopword(cur)) out.push_back(cur);
    return out;
}
