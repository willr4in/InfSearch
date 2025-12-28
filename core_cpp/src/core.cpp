#include "core_api.h"
#include <vector>
#include <string>
#include <cctype>
#include <cstring>
#include <algorithm>
#include <cstdlib>

// =================================================================================
// Memory Management Implementation
// =================================================================================
void free_string_array(StringArray arr) {
    if (!arr.strings) {
        return;
    }
    for (int i = 0; i < arr.count; ++i) {
        // These are now allocated with malloc
        free(arr.strings[i]);
    }
    free(arr.strings);
}

void free_single_string(char* str) {
    if (str) {
        // Memory from stemmer is allocated with malloc
        free(str);
    }
}


// =================================================================================
// Tokenizer Implementation (with STL)
// =================================================================================
namespace { // Anonymous namespace for internal helpers
    // Corrected version
void to_lower_utf8_stl(std::string& s) {
    for (size_t i = 0; i < s.length(); ++i) {
        unsigned char c1 = s[i];
        if (c1 >= 0xD0 && c1 <= 0xDF && i + 1 < s.length()) { // Cyrillic character
            unsigned char c2 = s[i+1];
            if (c1 == 0xD0 && c2 >= 0x90 && c2 <= 0x9F) { // А-П
                s[i+1] = s[i+1] + 32;
            } else if (c1 == 0xD0 && c2 >= 0xA0 && c2 <= 0xAF) { // Р-Я
                s[i] = 0xD1;
                s[i+1] = s[i+1] - 32;
            } else if (c1 == 0xD1 && c2 >= 0x80 && c2 <= 0x8F) { // а-п already lower
                 // do nothing
            } else if (c1 == 0xD1 && c2 == 0x91) { // Ё -> ё
                 s[i+1] = 0x91; // ё is 0xD1 0x91, Ё is 0xD0 0x81 -- this case is complex
            }
            i++; // skip second byte
        } else { // Not a Cyrillic char, use standard tolower
            s[i] = std::tolower(c1);
        }
    }
}
}

StringArray tokenize(const char* text) {
    if (!text) return {nullptr, 0};

    std::vector<std::string> tokens;
    std::string current_word;
    std::string input(text);

    for (size_t i = 0; i < input.length(); ) {
        size_t char_len = 1;
        unsigned char c = input[i];
        bool is_cyrillic = false;
        if (c >= 0xD0 && c <= 0xDF && i + 1 < input.length()) {
            char_len = 2;
            is_cyrillic = true;
        }

        if (isalpha(c) || is_cyrillic) {
            current_word += input.substr(i, char_len);
        } else {
            if (!current_word.empty()) {
                to_lower_utf8_stl(current_word);
                tokens.push_back(current_word);
                current_word.clear();
            }
        }
        i += char_len;
    }
    if (!current_word.empty()) {
        to_lower_utf8_stl(current_word);
        tokens.push_back(current_word);
    }

    StringArray result;
    result.count = tokens.size();
    result.strings = (char**)malloc(result.count * sizeof(char*));
    for (int i = 0; i < result.count; ++i) {
        result.strings[i] = (char*)malloc(tokens[i].length() + 1);
        strcpy(result.strings[i], tokens[i].c_str());
    }
    return result;
}


// =================================================================================
// Stemmer Implementation (NO STL)
// =================================================================================
namespace { // Anonymous namespace for internal helpers
    bool ends_with_no_stl(const char* word, const char* suffix) {
        size_t word_len = strlen(word);
        size_t suffix_len = strlen(suffix);
        if (word_len < suffix_len) return false;
        return strcmp(word + word_len - suffix_len, suffix) == 0;
    }

    char* replace_suffix_no_stl(const char* word, const char* old_suffix, const char* new_suffix) {
        size_t word_len = strlen(word);
        size_t old_suffix_len = strlen(old_suffix);
        size_t new_suffix_len = strlen(new_suffix);
        size_t new_word_len = word_len - old_suffix_len + new_suffix_len;
        
        char* new_word = (char*)malloc(new_word_len + 1);
        strncpy(new_word, word, word_len - old_suffix_len);
        strcpy(new_word + (word_len - old_suffix_len), new_suffix);
        new_word[new_word_len] = '\0';
        return new_word;
    }
}


// A simplified Porter stemmer for Russian.
char* stem_word_no_stl(const char* word) {
    if (!word || strlen(word) == 0) {
        char* empty = (char*)malloc(1);
        empty[0] = '\0';
        return empty;
    }

    char* result = (char*)malloc(strlen(word) + 1);
    strcpy(result, word);

    // Simple rules for demonstration
    if (ends_with_no_stl(result, "ами")) {
        char* temp = replace_suffix_no_stl(result, "ами", "");
        free(result);
        result = temp;
    } else if (ends_with_no_stl(result, "ого")) {
        char* temp = replace_suffix_no_stl(result, "ого", "");
        free(result);
        result = temp;
    }
    // ... more rules would be here in a full implementation

    return result;
}

// =================================================================================
// Core Version Implementation
// =================================================================================
const char* get_core_version() {
    return "0.1.1-alpha";
}
