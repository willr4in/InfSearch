cmake_minimum_required(VERSION 3.10)
project(InfSearchCore)

# --- Configuration ---
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable position independent code, necessary for shared libraries
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# --- File Globbing ---
# Find ALL source files in the src/ directory recursively
file(GLOB_RECURSE CORE_SOURCES "src/*.cpp")

# Create a shared library from ALL the found source files
add_library(core SHARED ${CORE_SOURCES})

# --- Include Directories ---
# Make sure the compiler can find our header files in include/
target_include_directories(core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# --- Installation (Optional but good practice) ---
# Defines where to install the library files if `make install` is run
install(TARGETS core DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)

