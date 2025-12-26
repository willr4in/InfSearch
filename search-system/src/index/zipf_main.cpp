#include "zipf_analyzer.h"
#include <cstdlib>
#include <string>
#include <iostream>

int main(int argc, char **argv) {
    const char *env = std::getenv("DATABASE_URL");
    std::string conn;
    if (env && env[0] != '\0') {
        conn = env;
        // normalize SQLAlchemy style URL (postgresql+psycopg2://) to libpq format
        const std::string tag = "+psycopg2";
        size_t pos = conn.find(tag);
        if (pos != std::string::npos) {
            conn.erase(pos, tag.size());
        }
    } else {
        conn = "postgresql://infsearch:infsearch@db:5432/infsearch";
    }

    int top_k = 10000;
    if (argc > 1) {
        try { top_k = std::stoi(argv[1]); } catch(...) {}
    }

    ZipfAnalyzer analyzer(conn);
    bool ok = analyzer.analyze(top_k);
    if (!ok) {
        std::cerr << "Zipf analysis failed" << std::endl;
        return 1;
    }
    return 0;
}
