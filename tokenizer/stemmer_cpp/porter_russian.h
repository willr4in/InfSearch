// tokenizer/stemmer_cpp/porter_russian.h
#pragma once

#ifdef _WIN32
    #define DLLEXPORT __declspec(dllexport)
#else
    #define DLLEXPORT
#endif

extern "C" {
    DLLEXPORT char* stem_word(const char* word);
    DLLEXPORT void free_stemmed_word(char* stemmed_word);
}

