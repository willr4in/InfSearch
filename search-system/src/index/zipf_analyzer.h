#pragma once

#include <string>

class ZipfAnalyzer {
public:
    ZipfAnalyzer(const std::string &conninfo);
    ~ZipfAnalyzer();

    // run analysis: compute frequencies, estimate alpha, store results
    bool analyze(int top_k = 10000);

private:
    std::string conninfo;
};
