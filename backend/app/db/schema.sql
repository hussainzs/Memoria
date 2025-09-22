CREATE EXTENSION IF NOT EXISTS vector;

DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('preference','fact','event','entity','media','skill','instruction');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE memory_visibility AS ENUM ('private','shared','public');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    type memory_type NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    content_summary TEXT,
    embedding VECTOR(384),
    tags TEXT[],
    entity_ids UUID[],
    source TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    last_recalled TIMESTAMP,
    recall_count INT DEFAULT 0,
    confidence FLOAT DEFAULT 0.5,
    visibility memory_visibility DEFAULT 'private',
    version INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS memory_links (
    id UUID PRIMARY KEY,
    src_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    dst_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_links_src ON memory_links(src_id);
CREATE INDEX IF NOT EXISTS idx_links_dst ON memory_links(dst_id);


