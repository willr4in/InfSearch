-- DDL for documents, sources, tokens

CREATE TABLE IF NOT EXISTS sources (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  rss_feed TEXT,
  last_crawled TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  title TEXT,
  content TEXT,
  content_hash TEXT UNIQUE,
  source_url TEXT UNIQUE,
  publish_date TIMESTAMP,
  category TEXT,
  word_count INTEGER,
  source_id INTEGER REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS tokens (
  id SERIAL PRIMARY KEY,
  token TEXT NOT NULL,
  stem TEXT,
  frequency INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_publish_date ON documents(publish_date);
