import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from scraper.scripts.climate_crawler import get_max_pages, extract_policy_links, extract_pdf_link, download_file, extract_text_from_pdf

@pytest.mark.asyncio
async def test_download_file_success(tmp_path):
    dest = tmp_path / "test.pdf"
    mock_client = MagicMock()
    
    # Mock the stream context manager
    mock_response = MagicMock() # Use MagicMock for the response to easily set non-async methods
    mock_response.status_code = 200
    
    async def mock_aiter_bytes():
        yield b"pdf content"
    
    mock_response.aiter_bytes.side_effect = mock_aiter_bytes
    
    stream_ctx = AsyncMock()
    stream_ctx.__aenter__.return_value = mock_response
    mock_client.stream.return_value = stream_ctx
    
    success = await download_file("http://example.com/test.pdf", str(dest), mock_client)
    
    assert success is True
    assert dest.exists()
    assert dest.read_bytes() == b"pdf content"

@pytest.mark.asyncio
async def test_download_file_failure(tmp_path):
    dest = tmp_path / "fail.pdf"
    mock_client = MagicMock()
    
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    stream_ctx = AsyncMock()
    stream_ctx.__aenter__.return_value = mock_response
    mock_client.stream.return_value = stream_ctx
    
    success = await download_file("http://example.com/fail.pdf", str(dest), mock_client)
    
    assert success is False
    assert not dest.exists()

@pytest.mark.asyncio
async def test_download_file_zero_bytes(tmp_path):
    dest = tmp_path / "zero.pdf"
    mock_client = MagicMock()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    async def mock_aiter_empty():
        if False: yield b"" # Ensure it's an async generator
    
    mock_response.aiter_bytes.side_effect = mock_aiter_empty
    
    stream_ctx = AsyncMock()
    stream_ctx.__aenter__.return_value = mock_response
    mock_client.stream.return_value = stream_ctx
    
    success = await download_file("http://example.com/zero.pdf", str(dest), mock_client)
    
    assert success is False
    assert not dest.exists()

def test_extract_text_from_pdf():
    with patch("pdfplumber.open") as mock_open:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted Text"
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf
        
        text = extract_text_from_pdf("fake.pdf")
        assert text == "Extracted Text"

def test_get_max_pages():
    html_with_last = """
    <ul class="pager">
        <li class="pager__item"><a href="?page=1">2</a></li>
        <li class="pager__item pager__item--last"><a href="?page=336">Last</a></li>
    </ul>
    """
    assert get_max_pages(html_with_last) == 336

    html_fallback = """
    <ul class="pager">
        <li class="pager__item"><a href="?page=1">2</a></li>
        <li class="pager__item"><a href="?page=5">6</a></li>
    </ul>
    """
    assert get_max_pages(html_fallback) == 5

    html_no_pager = "<div>No pager here</div>"
    assert get_max_pages(html_no_pager) == 0

def test_extract_policy_links():
    html = """
    <table>
        <tbody>
            <tr>
                <td class="views-field-title">
                    <a href="/policies/test-policy">Test Policy</a>
                </td>
            </tr>
            <tr>
                <td class="views-field-title">
                    <a href="https://climatepolicydatabase.org/policies/other">Other Policy</a>
                </td>
            </tr>
        </tbody>
    </table>
    """
    links = extract_policy_links(html)
    assert len(links) == 2
    assert links[0] == "https://climatepolicydatabase.org/policies/test-policy"
    assert links[1] == "https://climatepolicydatabase.org/policies/other"

def test_extract_pdf_link():
    # Test parent/child structure
    html_parent = """
    <div class="field">
        <div class="field__label">Source of reference</div>
        <div class="field__value"><a href="http://example.com/doc.pdf">Document</a></div>
    </div>
    """
    assert extract_pdf_link(html_parent) == "http://example.com/doc.pdf"

    # Test sibling structure
    html_sibling = """
    <div class="field__label">Source of reference</div>
    <div class="field__value"><a href="http://example.com/doc2.pdf">Document 2</a></div>
    """
    assert extract_pdf_link(html_sibling) == "http://example.com/doc2.pdf"

    # Test missing
    html_missing = """
    <div class="field">
        <div class="field__label">Some other field</div>
        <div class="field__value"><a href="http://example.com/doc.pdf">Document</a></div>
    </div>
    """
    assert extract_pdf_link(html_missing) is None
