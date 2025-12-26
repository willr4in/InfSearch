# Makefile для управления docker-compose
.PHONY: build up down test deploy

COMPOSE_FILE = docker-compose.yml

build:
	docker-compose -f $(COMPOSE_FILE) build

up:
	docker-compose -f $(COMPOSE_FILE) up -d --remove-orphans

down:
	docker-compose -f $(COMPOSE_FILE) down

test:
	@echo "Запуск тестов (если есть)"
	# Пример: docker-compose run --rm web pytest -q

deploy: build up
	@echo "Сервис запущен"

CXX=g++
CXXFLAGS=-std=c++17 -I/usr/include -I/usr/local/include -O2
LDFLAGS=-lpqxx -lpq -pthread

SRC_CPP=src/crawler/db_crawler.cpp src/crawler/document_processor.cpp src/db/postgres_connector.cpp

.PHONY: crawler-cpp
crawler-cpp:
	mkdir -p bin
	$(CXX) $(CXXFLAGS) $(SRC_CPP) -o bin/crawler $(LDFLAGS)

tokenizer: src/tokenizer/tokenizer_runner.cpp src/tokenizer/tokenizer.cpp src/stemmer/porter_russian.cpp src/db/postgres_connector.cpp
	mkdir -p bin
	g++ -std=c++17 $^ -o bin/tokenizer -lpqxx -lpq -pthread

.PHONY: zipf
zipf:
	mkdir -p bin
	# build and run inside the web container so the host doesn't need libpqxx dev packages
	sudo docker compose run --rm -v "$(CURDIR)":/app -w /app web bash -lc "g++ -std=c++17 src/index/zipf_analyzer.cpp src/db/postgres_connector.cpp -o bin/zipf_analyzer -lpqxx -lpq -pthread && ./bin/zipf_analyzer && python3 python/evaluation/plot_zipf.py"
