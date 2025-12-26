FROM postgres:15-alpine

# Копируем скрипты инициализации в папку, которую PostgreSQL выполняет при старте контейнера
COPY database/ /docker-entrypoint-initdb.d/
RUN chmod -R 755 /docker-entrypoint-initdb.d || true
