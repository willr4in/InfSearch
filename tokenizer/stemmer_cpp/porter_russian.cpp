// tokenizer/stemmer_cpp/porter_russian.cpp
#include "porter_russian.h"
#include <string>
#include <cstring>
#include <algorithm>
#include <vector>

namespace {
    // Helper functions for Russian Porter Stemmer
    bool is_vowel(wchar_t c) {
        return wcschr(L"аеёиоуыэюя", c) != nullptr;
    }

    std::wstring to_wstring(const std::string& str) {
        std::wstring wstr(str.size(), L' ');
        mbstowcs(&wstr[0], str.c_str(), str.size());
        return wstr;
    }
    
    std::string to_string(const std::wstring& wstr) {
        std::string str(wstr.size() * 4, ' ');
        size_t len = wcstombs(&str[0], wstr.c_str(), wstr.size() * 4);
        str.resize(len);
        return str;
    }

    bool ends_with(const std::wstring& word, const std::wstring& suffix) {
        if (word.length() < suffix.length()) return false;
        return word.substr(word.length() - suffix.length()) == suffix;
    }
    
    void replace_suffix(std::wstring& word, const std::wstring& old_suffix, const std::wstring& new_suffix) {
        if (ends_with(word, old_suffix)) {
            word = word.substr(0, word.length() - old_suffix.length()) + new_suffix;
        }
    }
}

std::string stem_russian_word(const std::string& word_str) {
    if (word_str.empty()) return "";
    
    setlocale(LC_ALL, "ru_RU.UTF-8");
    std::wstring word = to_wstring(word_str);

    // Step 1: Perfective Gerund
    if (ends_with(word, L"вшись")) {
        replace_suffix(word, L"вшись", L"");
    } else if (ends_with(word, L"шись")) {
        replace_suffix(word, L"шись", L"");
    } else if (ends_with(word, L"вшись")) {
         replace_suffix(word, L"вшись", L"");
    }

    // Step 2: Adjectival
    const std::vector<std::wstring> adjectival_endings = {L"ее", L"ие", L"ые", L"ое", L"ими", L"ыми", L"ей", L"ий", L"ый", L"ой", L"ем", L"им", L"ым", L"ом", L"его", L"ого", L"ему", L"ому", L"их", L"ых", L"ую", L"юю", L"ая", L"яя", L"ою", L"ею"};
    for (const auto& suffix : adjectival_endings) {
        if (ends_with(word, suffix)) {
            replace_suffix(word, suffix, L"");
            break;
        }
    }

    // Step 3: Verb
    const std::vector<std::wstring> verb_endings = {L"ла", L"на", L"ете", L"йте", L"ли", L"й", L"л", L"ем", L"н", L"ло", L"но", L"ет", L"ют", L"ны", L"ть", L"ешь", L"нно"};
     for (const auto& suffix : verb_endings) {
        if (ends_with(word, suffix)) {
            replace_suffix(word, suffix, L"");
            break;
        }
    }

    // Step 4: Noun
    const std::vector<std::wstring> noun_endings = {L"а", L"ев", L"ов", L"ие", L"ье", L"е", L"иями", L"ями", L"ами", L"еи", L"ии", L"и", L"ией", L"ей", L"ой", L"ий", L"й", L"иям", L"ям", L"ием", L"ем", L"ам", L"ом", L"о", L"у", L"ах", L"иях", L"ях", L"ы", L"ь", L"ию", L"ю", L"га", L"ка", L"на"};
    for (const auto& suffix : noun_endings) {
        if (ends_with(word, suffix)) {
            replace_suffix(word, suffix, L"");
            break;
        }
    }

    return to_string(word);
}

extern "C" {
    char* stem_word(const char* word) {
        std::string result_str = stem_russian_word(std::string(word));
        char* result = new char[result_str.length() + 1];
        strcpy(result, result_str.c_str());
        return result;
    }

    void free_stemmed_word(char* stemmed_word) {
        delete[] stemmed_word;
    }
}
