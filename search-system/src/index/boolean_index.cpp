#include <pqxx/pqxx>
#include <iostream>
#include <vector>
#include <unordered_map>
#include <map>
#include <string>
#include <chrono>
#include <fstream>
#include <cstdint>
#include <algorithm>

using namespace std;
using namespace pqxx;

static inline void set_bit(vector<unsigned char> &bits, size_t pos) {
    size_t byte_idx = pos / 8;
    size_t bit_idx = pos % 8;
    bits[byte_idx] |= (1u << (7 - bit_idx));
}

// Simple RLE over bytes: store pairs (value, 4-byte count BE) -> [val][count32][val][count32]...
static vector<unsigned char> rle_compress(const vector<unsigned char> &bits) {
    vector<unsigned char> out;
    if (bits.empty()) return out;
    unsigned char cur = bits[0];
    uint32_t cnt = 1;
    for (size_t i = 1; i < bits.size(); ++i) {
        if (bits[i] == cur) {
            ++cnt;
            if (cnt == 0xFFFFFFFFu) {
                // flush
                out.push_back(cur);
                out.push_back((cnt >> 24) & 0xFF);
                out.push_back((cnt >> 16) & 0xFF);
                out.push_back((cnt >> 8) & 0xFF);
                out.push_back((cnt) & 0xFF);
                cnt = 0;
            }
        } else {
            out.push_back(cur);
            out.push_back((cnt >> 24) & 0xFF);
            out.push_back((cnt >> 16) & 0xFF);
            out.push_back((cnt >> 8) & 0xFF);
            out.push_back((cnt) & 0xFF);
            cur = bits[i];
            cnt = 1;
        }
    }
    // flush
    out.push_back(cur);
    out.push_back((cnt >> 24) & 0xFF);
    out.push_back((cnt >> 16) & 0xFF);
    out.push_back((cnt >> 8) & 0xFF);
    out.push_back((cnt) & 0xFF);
    return out;
}

// Elias-gamma encoding helpers
static void append_bit(vector<unsigned char> &out, uint8_t bit, unsigned &bit_pos) {
    if (bit_pos == 0) out.push_back(0);
    if (bit) out.back() |= (1u << (7 - bit_pos));
    bit_pos = (bit_pos + 1) & 7u;
}

static void append_unary_and_binary(vector<unsigned char> &out, uint32_t value, unsigned &bit_pos) {
    // value >= 1
    unsigned l = 32 - __builtin_clz(value); // number of bits
    unsigned zeros = l - 1;
    for (unsigned i = 0; i < zeros; ++i) append_bit(out, 0, bit_pos);
    // write the value in l bits
    for (int i = l - 1; i >= 0; --i) append_bit(out, (value >> i) & 1u, bit_pos);
}

static vector<unsigned char> elias_gamma_compress_gaps(const vector<uint32_t> &doc_indices) {
    vector<unsigned char> out;
    unsigned bit_pos = 0; // position inside last byte [0..7]
    uint32_t prev = 0;
    for (uint32_t idx : doc_indices) {
        uint32_t gap = idx - prev; // gap >=1 because idx > prev
        if (gap == 0) gap = 1; // safety
        append_unary_and_binary(out, gap, bit_pos);
        prev = idx;
    }
    // if bit_pos != 0 then bytes already filled
    return out;
}

static string pg_array_literal(const vector<int> &v) {
    string s = "{";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += to_string(v[i]);
    }
    s += "}";
    return s;
}

int main(int argc, char **argv) {
    const char *env = getenv("DATABASE_URL");
    string connstr = env ? string(env) : string("postgresql://infsearch:infsearch@db:5432/infsearch");
    try {
        auto t0 = chrono::steady_clock::now();
        // use a dedicated read connection; create short-lived writer connections for writes
        connection conn_read(connstr);
        {
            // create tables using a short-lived writer connection so transaction is closed immediately
            connection tmp_w(connstr);
            work txn(tmp_w);
            txn.exec("CREATE TABLE IF NOT EXISTS inverted_index (token_id integer NOT NULL, document_id integer NOT NULL, positions integer[], PRIMARY KEY (token_id, document_id))");
            txn.exec("CREATE TABLE IF NOT EXISTS boolean_index (token_id integer PRIMARY KEY, bitmap bytea, compressed_rle bytea, compressed_gamma bytea)");
            txn.exec("CREATE INDEX IF NOT EXISTS idx_inverted_token ON inverted_index(token_id)");
            txn.commit();
        }

        // Fetch documents and build doc->index mapping
        pqxx::result docs;
        {
            work r1(conn_read);
            docs = r1.exec("SELECT id FROM documents ORDER BY id");
            r1.commit();
        }
        vector<int> doc_ids;
        doc_ids.reserve(docs.size());
        unordered_map<int,int> doc_to_idx;
        int idx = 0;
        for (auto row : docs) {
            int id = row[0].as<int>();
            doc_ids.push_back(id);
            doc_to_idx[id] = idx++;
        }
        int num_docs = (int)doc_ids.size();
        cout << "Found " << num_docs << " documents" << endl;

        // Build token -> id map from distinct tokens
        pqxx::result tokens_res;
        {
            work r2(conn_read);
            tokens_res = r2.exec("SELECT DISTINCT token FROM tokens");
            r2.commit();
        }
        unordered_map<string,int> token_to_id;
        token_to_id.reserve(tokens_res.size()*2 + 10);
        int token_id_counter = 1;
        for (auto row : tokens_res) {
            string tok = row[0].c_str();
            token_to_id[tok] = token_id_counter++;
        }
        cout << "Distinct tokens: " << token_to_id.size() << " -> next token_id=" << token_id_counter << endl;

        // Fetch all tokens ordered by token,document,position (loads into memory).
        // Simpler and avoids cursor transaction conflicts when performing concurrent writes.
        const int BATCH_TOKENS = 1000; // flush boolean_index every N tokens
        vector<pair<int, vector<unsigned char>>> boolean_rows; // token_id -> bitmap bytes
        boolean_rows.reserve(BATCH_TOKENS);

        int processed_tokens = 0;

        string cur_token;
        int cur_token_id = -1;
        int cur_doc = -1;
        vector<int> cur_positions;
        vector<pair<int, vector<int>>> postings_for_token; // docid -> positions

        pqxx::result all;
        {
            nontransaction fetch_conn(conn_read);
            all = fetch_conn.exec("SELECT token, document_id, position FROM tokens ORDER BY token, document_id, position");
        }
        for (auto row : all) {
            string tok = row[0].c_str();
            int docid = row[1].as<int>();
            int pos = row[2].as<int>();
            if (cur_token.empty()) {
                cur_token = tok;
                cur_token_id = token_to_id.count(cur_token) ? token_to_id[cur_token] : token_id_counter++;
                cur_doc = docid;
                cur_positions.clear();
                cur_positions.push_back(pos);
            } else if (tok == cur_token) {
                if (docid == cur_doc) {
                    cur_positions.push_back(pos);
                } else {
                    // flush current doc positions into postings
                    postings_for_token.emplace_back(cur_doc, cur_positions);
                    // start new doc
                    cur_doc = docid;
                    cur_positions.clear();
                    cur_positions.push_back(pos);
                }
            } else {
                // token changed -> flush last doc
                postings_for_token.emplace_back(cur_doc, cur_positions);

                // process postings_for_token: insert inverted_index rows and compute bitmap
                // Build bitmap
                vector<unsigned char> bitmap((num_docs + 7) / 8, 0);
                vector<uint32_t> present_doc_indices;
                present_doc_indices.reserve(postings_for_token.size());

                // Begin a transaction for inserting inverted_index for this token using a short-lived writer connection
                connection conn_w(connstr);
                work w(conn_w);
                for (auto &p : postings_for_token) {
                    int d = p.first;
                    const vector<int> &poses = p.second;
                    auto it = doc_to_idx.find(d);
                    if (it == doc_to_idx.end()) continue; // skip missing doc
                    int doc_idx = it->second;
                    set_bit(bitmap, doc_idx);
                    present_doc_indices.push_back((uint32_t)(doc_idx + 1)); // use 1-based indices in gaps

                    // insert inverted_index row: token_id, document_id, positions
                    string arr = pg_array_literal( (vector<int>)poses );
                    // use exec_params to be safer with quotes
                    w.exec_params("INSERT INTO inverted_index(token_id, document_id, positions) VALUES($1,$2,$3) ON CONFLICT (token_id, document_id) DO UPDATE SET positions=EXCLUDED.positions",
                                  cur_token_id, d, arr);
                }
                w.commit();

                // compress
                vector<unsigned char> rle = rle_compress(bitmap);
                vector<unsigned char> gamma = elias_gamma_compress_gaps(present_doc_indices);

                boolean_rows.emplace_back(cur_token_id, bitmap);

                // store compressed versions into boolean_index in batch later
                // clear for next token
                postings_for_token.clear();

                // start new token
                cur_token = tok;
                cur_token_id = token_to_id.count(cur_token) ? token_to_id[cur_token] : token_id_counter++;
                cur_doc = docid;
                cur_positions.clear();
                cur_positions.push_back(pos);

                // flush boolean rows in batch if needed
                if ((int)boolean_rows.size() >= BATCH_TOKENS) {
                    connection conn_w2(connstr);
                    work w2(conn_w2);
                    for (auto &br : boolean_rows) {
                        int tid = br.first;
                        // we need to recompute bitmap and compress; but we stored bitmap only. let's compress here.
                        vector<unsigned char> b = br.second;
                        vector<unsigned char> r = rle_compress(b);
                        // derive doc_indices for gamma from bitmap
                        vector<uint32_t> doc_indices;
                        for (size_t bi = 0; bi < (size_t)num_docs; ++bi) {
                            size_t byte_idx = bi / 8;
                            size_t bit_idx = bi % 8;
                            if (b[byte_idx] & (1u << (7 - bit_idx))) doc_indices.push_back((uint32_t)(bi + 1));
                        }
                        vector<unsigned char> g = elias_gamma_compress_gaps(doc_indices);
                        // insert into boolean_index
                        w2.exec_params("INSERT INTO boolean_index(token_id, bitmap, compressed_rle, compressed_gamma) VALUES($1,$2,$3,$4) ON CONFLICT (token_id) DO UPDATE SET bitmap=EXCLUDED.bitmap, compressed_rle=EXCLUDED.compressed_rle, compressed_gamma=EXCLUDED.compressed_gamma",
                                       tid, binarystring(reinterpret_cast<const char*>(b.data()), b.size()), binarystring(reinterpret_cast<const char*>(r.data()), r.size()), binarystring(reinterpret_cast<const char*>(g.data()), g.size()));
                    }
                    w2.commit();
                    boolean_rows.clear();
                }

                ++processed_tokens;
            }
        }

        // After loop, flush remaining current token
        if (!cur_token.empty()) {
            // flush last doc
            postings_for_token.emplace_back(cur_doc, cur_positions);
            vector<unsigned char> bitmap((num_docs + 7) / 8, 0);
            vector<uint32_t> present_doc_indices;
            connection conn_w_local(connstr);
            work w(conn_w_local);
            for (auto &p : postings_for_token) {
                int d = p.first;
                const vector<int> &poses = p.second;
                auto it = doc_to_idx.find(d);
                if (it == doc_to_idx.end()) continue;
                int doc_idx = it->second;
                set_bit(bitmap, doc_idx);
                present_doc_indices.push_back((uint32_t)(doc_idx + 1));
                string arr = pg_array_literal( (vector<int>)poses );
                w.exec_params("INSERT INTO inverted_index(token_id, document_id, positions) VALUES($1,$2,$3) ON CONFLICT (token_id, document_id) DO UPDATE SET positions=EXCLUDED.positions",
                              cur_token_id, d, arr);
            }
            w.commit();
            vector<unsigned char> rle = rle_compress(bitmap);
            vector<unsigned char> gamma = elias_gamma_compress_gaps(present_doc_indices);
            // insert boolean row using short-lived writer connection
            connection conn_w3(connstr);
            work w2(conn_w3);
            w2.exec_params("INSERT INTO boolean_index(token_id, bitmap, compressed_rle, compressed_gamma) VALUES($1,$2,$3,$4) ON CONFLICT (token_id) DO UPDATE SET bitmap=EXCLUDED.bitmap, compressed_rle=EXCLUDED.compressed_rle, compressed_gamma=EXCLUDED.compressed_gamma",
                           cur_token_id, binarystring(reinterpret_cast<const char*>(bitmap.data()), bitmap.size()), binarystring(reinterpret_cast<const char*>(rle.data()), rle.size()), binarystring(reinterpret_cast<const char*>(gamma.data()), gamma.size()));
            w2.commit();
            ++processed_tokens;
        }

        // flush any leftover boolean_rows
        if (!boolean_rows.empty()) {
            connection conn_w4(connstr);
            work w(conn_w4);
            for (auto &br : boolean_rows) {
                int tid = br.first;
                vector<unsigned char> b = br.second;
                vector<unsigned char> r = rle_compress(b);
                vector<uint32_t> doc_indices;
                for (size_t bi = 0; bi < (size_t)num_docs; ++bi) {
                    size_t byte_idx = bi / 8;
                    size_t bit_idx = bi % 8;
                    if (b[byte_idx] & (1u << (7 - bit_idx))) doc_indices.push_back((uint32_t)(bi + 1));
                }
                vector<unsigned char> g = elias_gamma_compress_gaps(doc_indices);
                w.exec_params("INSERT INTO boolean_index(token_id, bitmap, compressed_rle, compressed_gamma) VALUES($1,$2,$3,$4) ON CONFLICT (token_id) DO UPDATE SET bitmap=EXCLUDED.bitmap, compressed_rle=EXCLUDED.compressed_rle, compressed_gamma=EXCLUDED.compressed_gamma",
                              tid, binarystring(reinterpret_cast<const char*>(b.data()), b.size()), binarystring(reinterpret_cast<const char*>(r.data()), r.size()), binarystring(reinterpret_cast<const char*>(g.data()), g.size()));
            }
            w.commit();
            boolean_rows.clear();
        }

        // Measurements using a fresh read connection
        long long inv_rows = 0;
        long long size_inv = 0;
        long long size_bool = 0;
        double elapsed = 0.0;
        {
            connection conn_ro(connstr);
            nontransaction nt(conn_ro);
            auto res1 = nt.exec("SELECT count(*) FROM inverted_index");
            inv_rows = res1[0][0].as<long long>();
            auto res2 = nt.exec("SELECT pg_total_relation_size('inverted_index'), pg_total_relation_size('boolean_index')");
            size_inv = res2[0][0].as<long long>();
            size_bool = res2[0][1].as<long long>();
        }
        {
            auto t1 = chrono::steady_clock::now();
            elapsed = chrono::duration_cast<chrono::seconds>(t1 - t0).count();
        }

        cout << "Inverted rows: " << inv_rows << "\n";
        cout << "Size inverted_index: " << size_inv << " bytes\n";
        cout << "Size boolean_index: " << size_bool << " bytes\n";
        cout << "Elapsed: " << elapsed << " sec\n";

        // write report
        ofstream rep("docs/index_report.txt");
        rep << "inverted_rows=" << inv_rows << "\n";
        rep << "size_inverted=" << size_inv << "\n";
        rep << "size_boolean=" << size_bool << "\n";
        rep << "elapsed_sec=" << elapsed << "\n";
        rep.close();

        // Basic single-word search check: pick token from argv[1] or take a frequent one
        string query_token;
        if (argc > 1) query_token = argv[1];
        else {
            nontransaction nt2(conn_read);
            auto r = nt2.exec("SELECT token FROM tokens GROUP BY token ORDER BY COUNT(*) DESC LIMIT 1");
            if (!r.empty()) query_token = r[0][0].c_str();
        }
        if (!query_token.empty()) {
            try {
                cout << "Testing single-word search for token='"<<query_token<<"'...\n";
                connection conn_ro2(connstr);
                nontransaction nt3(conn_ro2);
                auto rtid = nt3.exec_params("SELECT token FROM tokens WHERE token=$1 LIMIT 1", query_token);
                int qtid = 0;
                if (!rtid.empty()) {
                    // fallback: we don't have canonical token_id in DB; map via token_to_id
                    auto it = token_to_id.find(query_token);
                    if (it != token_to_id.end()) qtid = it->second;
                } else {
                    auto it = token_to_id.find(query_token);
                    if (it != token_to_id.end()) qtid = it->second;
                }
                if (qtid == 0) {
                    cout << "Token id not found for test token\n";
                } else {
                    auto rb = nt3.exec_params("SELECT bitmap FROM boolean_index WHERE token_id=$1", qtid);
                    if (rb.empty()) cout << "No boolean entry for token_id="<<qtid<<"\n";
                    else {
                        string bmp = rb[0][0].as<string>();
                        // bmp may contain binary data; compute set bits
                        vector<int> found_docs;
                        for (size_t bi = 0; bi < (size_t)num_docs; ++bi) {
                            size_t byte_idx = bi / 8;
                            size_t bit_idx = bi % 8;
                            if ( (unsigned char)bmp[byte_idx] & (1u << (7-bit_idx)) ) {
                                found_docs.push_back(doc_ids[bi]);
                            }
                        }
                        cout << "Found "<<found_docs.size()<<" documents for token\n";
                        if (!found_docs.empty()) {
                            cout << "Example doc ids: ";
                            for (size_t i = 0; i < min<size_t>(found_docs.size(), 10); ++i) cout << found_docs[i] << " ";
                            cout << "\n";
                        }
                    }
                }
            } catch (const exception &e) {
                cerr << "Search error: " << e.what() << "\n";
            }
        }

        // connections will be closed by destructors
        (void)conn_read;

    } catch (const exception &e) {
        cerr << "Error: " << e.what() << endl;
        return 2;
    }
    return 0;
}
