#include "zipf_api.h"
#include "core_api.h"
#include <cstdlib>
#include <cstring>

// =================================================================================
// CUSTOM NON-STL HASH TABLE FOR FREQUENCIES
// =================================================================================

typedef struct FreqNode {
    char* key;
    int frequency;
    struct FreqNode* next;
} FreqNode;

struct FrequencyMap {
    FreqNode** buckets;
    int num_buckets;
    int total_stems;
};

// Using the same hash function as the indexer
extern unsigned int hash_func(const char* key, int num_buckets);

int compare_freq_pairs(const void* a, const void* b) {
    FreqPair* pairA = (FreqPair*)a;
    FreqPair* pairB = (FreqPair*)b;
    return (pairB->frequency - pairA->frequency);
}

// =================================================================================
// C API IMPLEMENTATION
// =================================================================================
extern "C" {
    FrequencyMap* create_freq_map() {
        FrequencyMap* map = (FrequencyMap*)malloc(sizeof(FrequencyMap));
        map->num_buckets = 20000; // Larger bucket size for lots of unique words
        map->buckets = (FreqNode**)calloc(map->num_buckets, sizeof(FreqNode*));
        map->total_stems = 0;
        return map;
    }

    void add_stems_to_freq_map(FrequencyMap* map, StringArray stems) {
        for (int i = 0; i < stems.count; ++i) {
            const char* stem = stems.strings[i];
            unsigned int bucket_index = hash_func(stem, map->num_buckets);
            bool found = false;

            for (FreqNode* current = map->buckets[bucket_index]; current != nullptr; current = current->next) {
                if (strcmp(current->key, stem) == 0) {
                    current->frequency++;
                    map->total_stems++;
                    found = true;
                    break; 
                }
            }

            if (found) {
                continue; // Move to the next stem
            }

            // Not found, create a new node
            FreqNode* new_node = (FreqNode*)malloc(sizeof(FreqNode));
            new_node->key = strdup(stem);
            new_node->frequency = 1;
            new_node->next = map->buckets[bucket_index];
            map->buckets[bucket_index] = new_node;
            map->total_stems++;
        }
    }

    FreqArray get_freq_map_as_array(FrequencyMap* map) {
        FreqArray array;
        array.count = 0;
        
        // First, count how many unique stems we have
        for(int i = 0; i < map->num_buckets; ++i) {
            for(FreqNode* node = map->buckets[i]; node != nullptr; node = node->next) {
                array.count++;
            }
        }

        array.pairs = (FreqPair*)malloc(sizeof(FreqPair) * array.count);
        
        // Now, populate the array
        int k = 0;
        for(int i = 0; i < map->num_buckets; ++i) {
            for(FreqNode* node = map->buckets[i]; node != nullptr; node = node->next) {
                array.pairs[k].stem = strdup(node->key);
                array.pairs[k].frequency = node->frequency;
                k++;
            }
        }

        // Sort the array by frequency
        qsort(array.pairs, array.count, sizeof(FreqPair), compare_freq_pairs);

        return array;
    }

    void destroy_freq_map(FrequencyMap* map) {
        if (!map) return;
        for (int i = 0; i < map->num_buckets; ++i) {
            FreqNode* current = map->buckets[i];
            while (current) {
                FreqNode* to_delete = current;
                current = current->next;
                free(to_delete->key);
                free(to_delete);
            }
        }
        free(map->buckets);
        free(map);
    }

    void free_freq_array(FreqArray arr) {
        if (!arr.pairs) return;
        for (int i = 0; i < arr.count; ++i) {
            free(arr.pairs[i].stem);
        }
        free(arr.pairs);
    }
}

