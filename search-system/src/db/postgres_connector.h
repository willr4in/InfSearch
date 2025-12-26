#pragma once

#include <pqxx/pqxx>
#include <string>

class PostgresConnector {
public:
    PostgresConnector();
    ~PostgresConnector();

    bool connect(const std::string &conninfo);
    pqxx::result execute(const std::string &sql);
    void disconnect();

private:
    pqxx::connection *conn;
};
