CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   VECTOR(1536), -- TODO: THIS SHOULD BE SAME AS EMBEDDING MODEL
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
)

CREATE INDEX ON memories USING hnsw (embedding vector_cosing_ops);