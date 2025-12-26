#pragma once

#include <string>
#include <vector>

class Tokenizer {
public:
    Tokenizer(const std::string &stopwords_path);
    ~Tokenizer();

    void load_stopwords();
    std::vector<std::string> tokenize(const std::string &text);

private:
    std::string stopwords_path;
    std::vector<std::string> stopwords;
    bool is_stopword(const std::string &w);
};
