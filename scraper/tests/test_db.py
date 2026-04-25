import pytest
from unittest.mock import AsyncMock, MagicMock
from scraper.config.db import is_downloaded, insert_document
from scraper.models.document import PolicyDocument

@pytest.fixture
def mock_pool():
    pool = MagicMock()
    # Create an async context manager for acquire()
    acquire_ctx = AsyncMock()
    conn = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    pool.acquire.return_value = acquire_ctx
    return pool, conn

@pytest.mark.asyncio
async def test_is_downloaded_true(mock_pool):
    pool, conn = mock_pool
    conn.fetchval.return_value = 1  # simulated ID

    result = await is_downloaded(pool, "http://example.com/doc.pdf")
    assert result is True
    conn.fetchval.assert_called_once()

@pytest.mark.asyncio
async def test_is_downloaded_false(mock_pool):
    pool, conn = mock_pool
    conn.fetchval.return_value = None

    result = await is_downloaded(pool, "http://example.com/doc.pdf")
    assert result is False

@pytest.mark.asyncio
async def test_insert_document(mock_pool):
    pool, conn = mock_pool
    conn.fetchval.return_value = 42

    doc = PolicyDocument(
        title="Test Policy",
        source_url="http://example.com/doc.pdf",
        file_path="data/policies/test.pdf",
        content="This is a test policy."
    )

    doc_id = await insert_document(pool, doc)
    assert doc_id == 42
    conn.fetchval.assert_called_once()
