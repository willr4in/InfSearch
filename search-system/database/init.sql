-- Инициализация базы данных для поисковой системы

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  title TEXT,
  body TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
  id SERIAL PRIMARY KEY,
  token TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS postings (
  id SERIAL PRIMARY KEY,
  token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
  doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  positions INTEGER[] -- позиции токена в документе
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token);
CREATE INDEX IF NOT EXISTS idx_postings_token_id ON postings(token_id);
CREATE INDEX IF NOT EXISTS idx_postings_doc_id ON postings(doc_id);
