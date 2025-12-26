Добавлены скрипты для скачивания корпуса и схемы БД.

- database/schemas/documents.sql — DDL для таблиц sources, documents, tokens
- config/crawler_config.yaml — конфигурация источников и параметры
- python/crawler/news_crawler.py — основной краулер, сохраняет статьи в PostgreSQL через SQLAlchemy
- scripts/download/download_corpus.py — запускает краулер, скачивает ~100 статей
- scripts/download/import_to_db.py — заглушка для импорта сырых файлов
- scripts/download/verify_corpus.py — проверяет количество документов в БД

Инструкции:
1) Убедитесь, что сервисы подняты: docker compose up -d --build
2) Установите python зависимости (локально или в контейнере web): pip install -r python/web_app/requirements.txt
3) Запустите:
   python3 scripts/download/download_corpus.py --limit 100
4) Проверьте: python3 scripts/download/verify_corpus.py
