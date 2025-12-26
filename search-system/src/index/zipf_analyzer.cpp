#include "zipf_analyzer.h"
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iostream>
#include "../db/postgres_connector.h"

ZipfAnalyzer::ZipfAnalyzer(const std::string &conninfo): conninfo(conninfo) {}
ZipfAnalyzer::~ZipfAnalyzer() {}

bool ZipfAnalyzer::analyze(int top_k) {
    PostgresConnector pg;
    if (!pg.connect(conninfo)) return false;

    // count frequencies
    pqxx::result r = pg.execute("SELECT token FROM tokens");
    std::unordered_map<std::string, long long> freq;
    for (auto row : r) {
        std::string t = row[0].c_str();
        freq[t]++;
    }

    std::vector<std::pair<std::string,long long>> vec;
    vec.reserve(freq.size());
    for (auto &p : freq) vec.emplace_back(p.first, p.second);
    std::sort(vec.begin(), vec.end(), [](auto &a, auto &b){ return a.second > b.second; });

    int n = std::min((int)vec.size(), top_k);
    // estimate alpha by linear regression on log(rank) vs log(freq)
    double sumx=0,sumy=0,sumxx=0,sumxy=0;
    for (int i=0;i<n;i++) {
        double rnk = i+1;
        double x = std::log(rnk);
        double y = std::log((double)vec[i].second);
        sumx += x; sumy += y; sumxx += x*x; sumxy += x*y;
    }
    double alpha = 0.0;
    if (n>1) {
        double slope = (n*sumxy - sumx*sumy) / (n*sumxx - sumx*sumx);
        alpha = -slope;
    }

    // save results into zipf_statistics
    pg.execute("CREATE TABLE IF NOT EXISTS zipf_statistics (rank integer PRIMARY KEY, token text, freq bigint, expected double precision)");
    // insert top n
    for (int i=0;i<n;i++) {
        double expected = std::pow((double)(i+1), -alpha);
        char buf[1024];
        int len = snprintf(buf, sizeof(buf), "INSERT INTO zipf_statistics(rank, token, freq, expected) VALUES (%d, '%s', %lld, %f) ON CONFLICT (rank) DO UPDATE SET token=EXCLUDED.token, freq=EXCLUDED.freq, expected=EXCLUDED.expected", i+1, vec[i].first.c_str(), vec[i].second, expected);
        pg.execute(std::string(buf, (len>0?len:0)));
    }

    // also save alpha value
    pg.execute("CREATE TABLE IF NOT EXISTS zipf_params (name text PRIMARY KEY, value double precision)");
    char buf[256];
    int l = snprintf(buf, sizeof(buf), "INSERT INTO zipf_params(name,value) VALUES ('alpha', %f) ON CONFLICT (name) DO UPDATE SET value=EXCLUDED.value", alpha);
    pg.execute(std::string(buf, (l>0?l:0)));

    pg.disconnect();
    std::cout << "Estimated alpha="<<alpha<<"\n";
    return true;
}
