#ifndef ZIPF_API_H
#define ZIPF_API_H

#include "core_api.h"

// Opaque pointer to the internal frequency map structure
typedef struct FrequencyMap FrequencyMap;

// A struct to hold a single term-frequency pair
typedef struct {
    char* stem;
    int frequency;
} FreqPair;

// A struct to hold an array of FreqPairs
typedef struct {
    FreqPair* pairs;
    int count;
} FreqArray;

extern "C" {
    /**
     * @brief Creates a new, empty frequency map in memory.
     */
    CORE_API FrequencyMap* create_freq_map();

    /**
     * @brief Adds stems to the frequency map, incrementing their counts.
     */
    CORE_API void add_stems_to_freq_map(FrequencyMap* map, StringArray stems);

    /**
     * @brief Converts the frequency map to a sorted array of pairs.
     * The array is sorted by frequency in descending order.
     * The caller is responsible for freeing the returned FreqArray with free_freq_array.
     */
    CORE_API FreqArray get_freq_map_as_array(FrequencyMap* map);

    /**
     * @brief Destroys the frequency map and frees all associated memory.
     */
    CORE_API void destroy_freq_map(FrequencyMap* map);

    /**
     * @brief Frees a FreqArray returned by the library.
     */
    CORE_API void free_freq_array(FreqArray arr);
}

#endif // ZIPF_API_H

