#ifndef CORE_API_H
#define CORE_API_H

#ifdef _WIN32
    #ifdef CORE_EXPORTS
        #define CORE_API __declspec(dllexport)
    #else
        #define CORE_API __declspec(dllimport)
    #endif
#else
    #define CORE_API
#endif

// Include tokenizer definitions AFTER CORE_API is defined
#include "tokenizer.h"

#include "zipf_api.h"

extern "C" {
    CORE_API const char* get_core_version();
}

#endif // CORE_API_H
