"""Database migration script for memory tables.

Creates the tables needed for the memory systems:
- health_episodic_memory (with pgvector)
- health_user_goals
- health_baselines

Run this script once to set up the database schema.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL statements to create tables
CREATE_TABLES_SQL = """
-- Enable pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Agent conversation state (LangGraph checkpointer)
-- Note: LangGraph creates its own tables, but we document the expected structure
-- CREATE TABLE IF NOT EXISTS checkpoints (
--     thread_id TEXT NOT NULL,
--     checkpoint_id TEXT NOT NULL,
--     parent_id TEXT,
--     checkpoint JSONB NOT NULL,
--     metadata JSONB,
--     created_at TIMESTAMP DEFAULT NOW(),
--     PRIMARY KEY (thread_id, checkpoint_id)
-- );

-- Episodic memory with vector search
CREATE TABLE IF NOT EXISTS health_episodic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    session_id TEXT,
    summary TEXT NOT NULL,
    query TEXT,
    outcome TEXT,
    health_metrics JSONB,
    embedding vector(768),  -- nomic-embed-text dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS health_episodic_memory_embedding_idx
ON health_episodic_memory USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS health_episodic_memory_user_idx
ON health_episodic_memory (user_id, created_at DESC);

-- User health goals
CREATE TABLE IF NOT EXISTS health_user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    goal_type TEXT NOT NULL,  -- sleep_duration, step_count, hrv_target, etc.
    target_value NUMERIC,
    target_text TEXT,
    status TEXT DEFAULT 'active',  -- active, achieved, abandoned, replaced
    created_at TIMESTAMP DEFAULT NOW(),
    achieved_at TIMESTAMP
);

-- Index for active goals lookup
CREATE INDEX IF NOT EXISTS health_user_goals_user_active_idx
ON health_user_goals (user_id, status) WHERE status = 'active';

-- Computed baselines for personalization
CREATE TABLE IF NOT EXISTS health_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    metric TEXT NOT NULL,  -- hrv_avg, resting_hr, sleep_efficiency, etc.
    baseline_value NUMERIC NOT NULL,
    sample_size INT,
    computed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, metric)
);

-- Index for baseline lookups
CREATE INDEX IF NOT EXISTS health_baselines_user_idx
ON health_baselines (user_id);
"""

# SQL function for similarity search
CREATE_SEARCH_FUNCTION_SQL = """
-- Function to search episodic memory by similarity
CREATE OR REPLACE FUNCTION search_health_memory(
    query_embedding vector(768),
    match_user_id TEXT,
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    user_id TEXT,
    session_id TEXT,
    summary TEXT,
    query TEXT,
    outcome TEXT,
    health_metrics JSONB,
    created_at TIMESTAMP,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.user_id,
        e.session_id,
        e.summary,
        e.query,
        e.outcome,
        e.health_metrics,
        e.created_at,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM health_episodic_memory e
    WHERE e.user_id = match_user_id
      AND 1 - (e.embedding <=> query_embedding) >= match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""


async def create_tables(connection_string: str) -> bool:
    """Create the memory tables.

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        True if successful
    """
    engine = get_engine(connection_string)

    try:
        async with engine.begin() as conn:
            # Create tables
            logger.info("Creating memory tables...")
            await conn.execute(text(CREATE_TABLES_SQL))

            # Create search function
            logger.info("Creating search function...")
            await conn.execute(text(CREATE_SEARCH_FUNCTION_SQL))

            logger.info("Memory tables created successfully!")
            return True

    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


async def main():
    """Run the migration."""
    import os

    # Try to load config, fall back to environment variable
    try:
        from src.config import get_config

        config = get_config()
        connection_string = config.database.connection_string
    except Exception:
        connection_string = os.getenv("DATABASE_URL")
        if not connection_string:
            logger.error("DATABASE_URL environment variable required")
            return 1

    logger.info("Running memory table migration...")
    success = await create_tables(connection_string)

    if success:
        logger.info("Migration completed successfully!")
        return 0
    else:
        logger.error("Migration failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
