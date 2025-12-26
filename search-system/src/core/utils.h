// Утилиты — заглушка
#pragma once

#include <string>
#include <algorithm>

inline std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}
