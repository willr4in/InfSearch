#include "../db/postgres_connector.h"
#include "document_processor.h"
#include <thread>
#include <vector>
#include <iostream>
#include <fstream>
#include <atomic>

static const int NUM_THREADS = 4;

void worker_thread(PostgresConnector *pg, std::vector<std::tuple<std::string,std::string,std::string>> *jobs, int thread_id, std::ofstream &logf) {
    DocumentProcessor proc;
    static std::atomic<size_t> idx{0};

    auto escape_sql = [](const std::string &s)->std::string {
        std::string r;
        r.reserve(s.size());
        for (char c : s) {
            if (c == '\'') r += "''"; else r += c;
        }
        return r;
    };

    while (true) {
        size_t myidx = idx.fetch_add(1);
        if (myidx >= jobs->size()) break;
        auto &job = (*jobs)[myidx];
        std::string id = std::get<0>(job);
        std::string title = std::get<1>(job);
        std::string content = std::get<2>(job);

        auto md = proc.process(title, content, id);
        // store metadata
        try {
            std::string esc_id = escape_sql(md.id);
            std::string sql = "INSERT INTO document_metadata(document_id, word_count, title_length) VALUES ('" + esc_id + "', " + std::to_string(md.word_count) + ", " + std::to_string(md.title_len) + ") ON CONFLICT (document_id) DO NOTHING";
            pg->execute(sql);
            logf << "Thread " << thread_id << " processed " << id << " words=" << md.word_count << "\n";
        } catch (const std::exception &e) {
            logf << "Thread " << thread_id << " error: " << e.what() << "\n";
        }
    }
}

int main(int argc, char **argv) {
    std::string conninfo = "host=db user=infsearch password=infsearch dbname=infsearch";
    PostgresConnector pg;
    if (!pg.connect(conninfo)) {
        std::cerr << "Failed to connect to Postgres" << std::endl;
        return 1;
    }

    // ensure metadata table exists
    try {
        pg.execute("CREATE TABLE IF NOT EXISTS document_metadata (\n            document_id text PRIMARY KEY,\n            word_count integer,\n            title_length integer,\n            processed_at timestamptz DEFAULT now()\n        )");
    } catch (const std::exception &e) {
        std::cerr << "Failed to ensure metadata table: " << e.what() << std::endl;
        // continue anyway
    }

    // read documents
    pqxx::result r = pg.execute("SELECT id, title, content FROM documents LIMIT 1000");
    std::vector<std::tuple<std::string,std::string,std::string>> jobs;
    for (auto row : r) {
        std::string id = row[0].c_str();
        std::string title = row[1].c_str();
        std::string content = row[2].c_str();
        jobs.emplace_back(id, title, content);
    }

    std::ofstream logf("crawler.log", std::ios::app);
    std::vector<std::thread> threads;
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back(worker_thread, &pg, &jobs, i, std::ref(logf));
    }

    for (auto &t : threads) t.join();

    pg.disconnect();
    return 0;
}
