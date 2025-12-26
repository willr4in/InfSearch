#pragma once

#include <string>

struct DocMetadata {
    std::string id;
    int word_count;
    int title_len;
};

class DocumentProcessor {
public:
    DocumentProcessor();
    DocMetadata process(const std::string &title, const std::string &content, const std::string &url);
};
