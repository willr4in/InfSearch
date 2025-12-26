#include "postgres_connector.h"
#include <iostream>

PostgresConnector::PostgresConnector(): conn(nullptr) {}

PostgresConnector::~PostgresConnector() {
    disconnect();
}

bool PostgresConnector::connect(const std::string &conninfo) {
    try {
        conn = new pqxx::connection(conninfo);
        return conn->is_open();
    } catch (const std::exception &e) {
        std::cerr << "Failed to connect: " << e.what() << std::endl;
        return false;
    }
}

pqxx::result PostgresConnector::execute(const std::string &sql) {
    if (!conn || !conn->is_open()) {
        throw std::runtime_error("Not connected");
    }
    pqxx::work txn(*conn);
    pqxx::result res = txn.exec(sql);
    txn.commit();
    return res;
}

void PostgresConnector::disconnect() {
    if (conn) {
        try {
            // let destructor handle closing the connection; avoid calling unavailable API
            delete conn;
        } catch (...) {}
        conn = nullptr;
    }
}
