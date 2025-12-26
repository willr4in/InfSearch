FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Скопировать весь проект, чтобы скрипты в корне были доступны
COPY . /app

# Установить системные зависимости для сборки C++ и Python расширений
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential g++ libpq-dev libpqxx-dev pkg-config python3-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Установить зависимости Python и psycopg2-бинарный (чтобы импорт psycopg2 работал)
RUN pip install --no-cache-dir -r /app/python/web_app/requirements.txt \
    && pip install --no-cache-dir psycopg2-binary matplotlib

EXPOSE 8000
CMD ["gunicorn", "--chdir", "python/web_app", "--bind", "0.0.0.0:8000", "app:app"]
