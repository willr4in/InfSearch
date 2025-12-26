#pragma once

#include <string>
#include <unordered_map>
#include <vector>

using PostingList = std::vector<int>;

class BooleanIndex {
public:
    void add(int doc_id, const std::string &term);
    PostingList get(const std::string &term) const;
private:
    std::unordered_map<std::string, PostingList> index_;
};
