#include "../db/postgres_connector.h"
#include "tokenizer.h"
#include "../stemmer/porter_russian.h"
#include <vector>
#include <iostream>

int main(int argc, char **argv) {
    std::string conninfo = "host=db user=infsearch password=infsearch dbname=infsearch";
    PostgresConnector pg;
    if (!pg.connect(conninfo)) {
        std::cerr << "DB connect failed" << std::endl;
        return 1;
    }

    // ensure tokens table
    pg.execute("CREATE TABLE IF NOT EXISTS tokens (id serial PRIMARY KEY, document_id text, token text, stem text, position integer)");
    pg.execute("CREATE INDEX IF NOT EXISTS idx_tokens_doc ON tokens(document_id)");
    pg.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token)");

    Tokenizer tokenizer("data/stopwords.txt");
    PorterRussian stemmer;

    pqxx::result r = pg.execute("SELECT id, content FROM documents LIMIT 1000");
    for (auto row : r) {
        std::string docid = row[0].c_str();
        std::string content = row[1].c_str();
        auto toks = tokenizer.tokenize(content);
        // batch insert simple
        int pos = 0;
        for (auto &t : toks) {
            std::string stem = stemmer.stem(t);
            char buf[1024];
            int n = snprintf(buf, sizeof(buf), "INSERT INTO tokens(document_id, token, stem, position) VALUES ('%s','%s','%s', %d)", docid.c_str(), t.c_str(), stem.c_str(), pos);
            std::string sql(buf, (n>0?n:0));
            pg.execute(sql);
            pos++;
        }
    }

    pg.disconnect();
    return 0;
}
