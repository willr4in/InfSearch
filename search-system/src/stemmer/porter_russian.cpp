#include "porter_russian.h"
#include <string>
#include <algorithm>
#include <cstring>

PorterRussian::PorterRussian() {}

static bool is_vowel(char c) {
    // simplified vowel check for ASCII and common Cyrillic bytes (placeholder)
    const char vowels[] = "aeiouyAEIOUY\xC0\xC1\xC2\xC3\xC4\xC5\xD0\xD1\xD2\xD3\xD4\xD5";
    return (c != 0 && strchr(vowels, c) != nullptr);
}

std::string PorterRussian::stem(const std::string &word) {
    if (word.size() <= 2) return word;
    std::string w = word;
    // very simplified: remove common endings
    const char *suffixes[] = {"ами","ями","ами","ях","иями","иями","ий","ь","ы","а","я","е","и","ом","ем","ов","ев","ую","ю","у","ом","ах","ой","ей", nullptr};
    for (int i=0; suffixes[i]; ++i) {
        std::string s = suffixes[i];
        if (w.size() > s.size() && w.compare(w.size()-s.size(), s.size(), s) == 0) {
            w.erase(w.size()-s.size());
            break;
        }
    }
    return w;
}
