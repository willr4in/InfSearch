# tokenizer/stemmer_cpp/CMakeLists.txt
# CMake file for the C++ stemmer
cmake_minimum_required(VERSION 3.10)
project(stemmer_cpp)

add_library(stemmer SHARED porter_russian.cpp)

install(TARGETS stemmer DESTINATION lib)

