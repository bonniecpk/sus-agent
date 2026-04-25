import json
import logging
from typing import Optional

import asyncpg

from scraper.models.document import PolicyDocument

logger = logging.getLogger(__name__)

# Default connection settings - override in production or use env vars
DB_DSN = "postgres://postgres:postgres@localhost:5432/climate"

async def get_pool() -> asyncpg.Pool:
    """Gets a connection pool to the PostgreSQL database."""
    return await asyncpg.create_pool(dsn=DB_DSN)

async def init_db(pool: asyncpg.Pool) -> None:
    """Initializes the database schema including the vector extension."""
    async with pool.acquire() as conn:
        # Create pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL,
                embedding vector(1536)
            );
        """)
        
        # Create an index on metadata to quickly look up source_url for idempotency
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_metadata_source_url 
            ON documents USING gin (metadata);
        """)
        logger.info("Database initialized successfully.")

async def is_downloaded(pool: asyncpg.Pool, source_url: str) -> bool:
    """Checks if a document with the given source_url already exists."""
    async with pool.acquire() as conn:
        query = """
            SELECT 1 
            FROM documents 
            WHERE metadata->>'source_url' = $1 
            LIMIT 1;
        """
        result = await conn.fetchval(query, source_url)
        return result is not None

async def insert_document(pool: asyncpg.Pool, doc: PolicyDocument) -> int:
    """Inserts a document into the database and returns its ID."""
    async with pool.acquire() as conn:
        query = """
            INSERT INTO documents (content, metadata, embedding)
            VALUES ($1, $2, $3)
            RETURNING id;
        """
        metadata_json = json.dumps(doc.to_metadata())
        
        # Note: If embedding is None, it will insert NULL.
        # If it's a list, we need to cast it properly for pgvector.
        # pgvector accepts strings like '[1,2,3]'
        embedding_str = None
        if doc.embedding is not None:
            embedding_str = f"[{','.join(str(x) for x in doc.embedding)}]"
            
        doc_id = await conn.fetchval(query, doc.content, metadata_json, embedding_str)
        logger.info(f"Inserted document ID {doc_id} for URL: {doc.source_url}")
        return doc_id
