#ifndef TOKENIZER_H
#define TOKENIZER_H

// The CORE_API macro should be defined by core_api.h before this file is included.

// A struct to represent an array of strings, returned from C++ to Python.
typedef struct {
    char** strings;
    int count;
} StringArray;

extern "C" {
    /**
     * @brief Tokenizes a given text into words.
     */
    CORE_API StringArray tokenize(const char* text);
    
    /**
     * @brief Stems a single word using a non-STL implementation.
     */
    CORE_API char* stem_word_no_stl(const char* word);
    
    /**
     * @brief Frees the memory allocated for a StringArray.
     */
    CORE_API void free_string_array(StringArray arr);

    /**
     * @brief Frees a single C-string allocated by the library.
     */
    CORE_API void free_single_string(char* str);
}

#endif // TOKENIZER_H
