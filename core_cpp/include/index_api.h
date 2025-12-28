#ifndef INDEX_API_H
#define INDEX_API_H

#include "core_api.h" // For CORE_API macro

// Opaque pointer to the internal index structure.
// Python will only ever see this as a generic pointer.
typedef struct InvertedIndex InvertedIndex;

// A struct to represent an array of integers, returned from C++ to Python.
typedef struct {
    int* ids;
    int count;
} IntArray;

extern "C" {
    /**
     * @brief Creates a new, empty inverted index in memory.
     * @return A pointer to the new index. Must be freed with destroy_index.
     */
    CORE_API InvertedIndex* create_index();

    /**
     * @brief Adds a document's stems to the index.
     * @param index Pointer to the index.
     * @param doc_id The unique ID of the document.
     * @param stems A StringArray of stems from the document.
     */
    CORE_API void add_document_to_index(InvertedIndex* index, int doc_id, StringArray stems);

    /**
     * @brief Saves the index to a binary file.
     * @param index Pointer to the index.
     * @param path Path to the file.
     * @return 0 on success, -1 on error.
     */
    CORE_API int save_index_to_file(const InvertedIndex* index, const char* path);

    /**
     * @brief Loads an index from a binary file.
     * @param path Path to the file.
     * @return A pointer to the loaded index. Must be freed with destroy_index. Returns NULL on error.
     */
    CORE_API InvertedIndex* load_index_from_file(const char* path);

    /**
     * @brief Performs a boolean search query on the index.
     * The query string should be simple for now, e.g., "word1 AND word2 OR word3 NOT word4".
     * @param index Pointer to the index.
     * @param query The boolean query string.
     * @return An IntArray of matching document IDs. Must be freed with free_int_array.
     */
    CORE_API IntArray search_index(const InvertedIndex* index, const char* query);

    /**
     * @brief Destroys the index and frees all associated memory.
     * @param index Pointer to the index to be destroyed.
     */
    CORE_API void destroy_index(InvertedIndex* index);

    /**
     * @brief Frees an IntArray returned by the search function.
     * @param arr The IntArray to free.
     */
    CORE_API void free_int_array(IntArray arr);
}

#endif // INDEX_API_H

