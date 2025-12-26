#include "document_processor.h"
#include <cctype>

DocumentProcessor::DocumentProcessor() {}

DocMetadata DocumentProcessor::process(const std::string &title, const std::string &content, const std::string &url) {
    DocMetadata md;
    md.id = url;

    // count words (simple)
    int wc = 0;
    bool in_word = false;
    for (size_t i = 0; i < content.size(); ++i) {
        char c = content[i];
        if (std::isspace(static_cast<unsigned char>(c))) {
            if (in_word) { wc++; in_word = false; }
        } else {
            in_word = true;
        }
    }
    if (in_word) wc++;
    md.word_count = wc;
    md.title_len = static_cast<int>(title.size());
    return md;
}
