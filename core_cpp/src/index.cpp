#include "index_api.h"
#include "core_api.h"
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <iterator>
#include <set>

// =================================================================================
// CUSTOM NON-STL DATA STRUCTURES
// =================================================================================
typedef struct { int* data; int size; int capacity; } DynamicIntArray;
typedef struct HashNode { char* key; DynamicIntArray* doc_ids; struct HashNode* next; } HashNode;
struct InvertedIndex { HashNode** buckets; int num_buckets; };
// ... (Implementation of DynamicIntArray and HashTable from previous step remains the same)
// ... (create_dynamic_array, da_push_back, destroy_dynamic_array, hash, create_index_internal, etc.)

DynamicIntArray* create_dynamic_array() {
    DynamicIntArray* arr = (DynamicIntArray*)malloc(sizeof(DynamicIntArray));
    arr->data = (int*)malloc(sizeof(int) * 8);
    arr->size = 0;
    arr->capacity = 8;
    return arr;
}
void da_push_back(DynamicIntArray* arr, int value) {
    if (arr->size == arr->capacity) {
        arr->capacity *= 2;
        arr->data = (int*)realloc(arr->data, sizeof(int) * arr->capacity);
    }
    arr->data[arr->size++] = value;
}
void destroy_dynamic_array(DynamicIntArray* arr) {
    free(arr->data);
    free(arr);
}
unsigned int hash_func(const char* key, int num_buckets) {
    unsigned long hash = 5381;
    int c;
    while ((c = *key++)) hash = ((hash << 5) + hash) + c;
    return hash % num_buckets;
}
InvertedIndex* create_index_internal(int num_buckets) {
    InvertedIndex* index = (InvertedIndex*)malloc(sizeof(InvertedIndex));
    index->num_buckets = num_buckets;
    index->buckets = (HashNode**)calloc(num_buckets, sizeof(HashNode*));
    return index;
}
void destroy_index_internal(InvertedIndex* index) {
    for (int i = 0; i < index->num_buckets; ++i) {
        HashNode* current = index->buckets[i];
        while (current) {
            HashNode* to_delete = current;
            current = current->next;
            free(to_delete->key);
            destroy_dynamic_array(to_delete->doc_ids);
            free(to_delete);
        }
    }
    free(index->buckets);
    free(index);
}


// =================================================================================
// SEARCH LOGIC (using STL internally for parsing and set operations)
// =================================================================================
namespace {
    std::vector<std::string> split_query(const std::string& query) {
        std::istringstream iss(query);
        return std::vector<std::string>{std::istream_iterator<std::string>{iss}, std::istream_iterator<std::string>{}};
    }

    DynamicIntArray* find_term_ids(const InvertedIndex* index, const std::string& term) {
        unsigned int bucket_index = hash_func(term.c_str(), index->num_buckets);
        HashNode* current = index->buckets[bucket_index];
        while (current) {
            if (strcmp(current->key, term.c_str()) == 0) {
                return current->doc_ids;
            }
            current = current->next;
        }
        return nullptr;
    }
}

// =================================================================================
// C API IMPLEMENTATION
// =================================================================================
extern "C" {
    // ... (create_index, add_document_to_index, destroy_index remain the same)
    InvertedIndex* create_index() { return create_index_internal(10000); }
    void add_document_to_index(InvertedIndex* index, int doc_id, StringArray stems) { /* ... same as before ... */ 
        for (int i = 0; i < stems.count; ++i) {
            const char* stem = stems.strings[i];
            unsigned int bucket_index = hash_func(stem, index->num_buckets);
            HashNode* current = index->buckets[bucket_index], *prev = nullptr;
            while (current != nullptr && strcmp(current->key, stem) != 0) {
                prev = current; current = current->next;
            }
            if (current == nullptr) {
                HashNode* new_node = (HashNode*)malloc(sizeof(HashNode));
                new_node->key = strdup(stem);
                new_node->doc_ids = create_dynamic_array();
                new_node->next = nullptr;
                da_push_back(new_node->doc_ids, doc_id);
                if (prev == nullptr) index->buckets[bucket_index] = new_node;
                else prev->next = new_node;
            } else {
                DynamicIntArray* ids = current->doc_ids; bool found = false;
                for (int j = 0; j < ids->size; ++j) if (ids->data[j] == doc_id) { found = true; break; }
                if (!found) da_push_back(ids, doc_id);
            }
        }
    }
    void destroy_index(InvertedIndex* index) { if (index) destroy_index_internal(index); }
    void free_int_array(IntArray arr) { if (arr.ids) free(arr.ids); }

    // --- SAVE/LOAD & SEARCH IMPLEMENTATION ---
    int save_index_to_file(const InvertedIndex* index, const char* path) {
        FILE* fp = fopen(path, "wb");
        if (!fp) return -1;

        fwrite(&index->num_buckets, sizeof(int), 1, fp);
        for (int i = 0; i < index->num_buckets; ++i) {
            HashNode* current = index->buckets[i];
            while (current) {
                int key_len = strlen(current->key);
                fwrite(&key_len, sizeof(int), 1, fp);
                fwrite(current->key, sizeof(char), key_len, fp);
                fwrite(&current->doc_ids->size, sizeof(int), 1, fp);
                fwrite(current->doc_ids->data, sizeof(int), current->doc_ids->size, fp);
                current = current->next;
            }
        }
        fclose(fp);
        return 0;
    }

    InvertedIndex* load_index_from_file(const char* path) {
        FILE* fp = fopen(path, "rb");
        if (!fp) return nullptr;

        int num_buckets;
        fread(&num_buckets, sizeof(int), 1, fp);
        InvertedIndex* index = create_index_internal(num_buckets);

        while (!feof(fp)) {
            int key_len, num_ids;
            if (fread(&key_len, sizeof(int), 1, fp) != 1) break;
            
            char* key = (char*)malloc(key_len + 1);
            fread(key, sizeof(char), key_len, fp);
            key[key_len] = '\0';
            
            fread(&num_ids, sizeof(int), 1, fp);
            DynamicIntArray* ids = create_dynamic_array();
            for(int i=0; i<num_ids; ++i) {
                int doc_id;
                fread(&doc_id, sizeof(int), 1, fp);
                da_push_back(ids, doc_id);
            }

            unsigned int bucket = hash_func(key, num_buckets);
            HashNode* new_node = (HashNode*)malloc(sizeof(HashNode));
            new_node->key = key;
            new_node->doc_ids = ids;
            new_node->next = index->buckets[bucket];
            index->buckets[bucket] = new_node;
        }
        fclose(fp);
        return index;
    }

    IntArray search_index(const InvertedIndex* index, const char* query) {
        auto tokens = split_query(query);
        if (tokens.empty()) return {nullptr, 0};

        std::set<int> result_ids;
        DynamicIntArray* initial_ids = find_term_ids(index, tokens[0]);
        if (initial_ids) {
            result_ids.insert(initial_ids->data, initial_ids->data + initial_ids->size);
        }

        for (size_t i = 1; i < tokens.size(); i += 2) {
            if (i + 1 >= tokens.size()) break;
            std::string op = tokens[i];
            std::string term = tokens[i+1];
            DynamicIntArray* term_ids_arr = find_term_ids(index, term);
            
            std::set<int> term_ids;
            if(term_ids_arr) {
                term_ids.insert(term_ids_arr->data, term_ids_arr->data + term_ids_arr->size);
            }

            if (op == "AND") {
                std::set<int> intersection;
                std::set_intersection(result_ids.begin(), result_ids.end(), term_ids.begin(), term_ids.end(),
                                      std::inserter(intersection, intersection.begin()));
                result_ids = intersection;
            } else if (op == "OR") {
                result_ids.insert(term_ids.begin(), term_ids.end());
            } else if (op == "NOT") {
                std::set<int> difference;
                std::set_difference(result_ids.begin(), result_ids.end(), term_ids.begin(), term_ids.end(),
                                    std::inserter(difference, difference.begin()));
                result_ids = difference;
            }
        }
        
        IntArray final_result;
        final_result.count = result_ids.size();
        final_result.ids = (int*)malloc(sizeof(int) * final_result.count);
        std::copy(result_ids.begin(), result_ids.end(), final_result.ids);
        return final_result;
    }
}
