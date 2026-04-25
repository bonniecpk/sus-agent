import os
import re
import asyncio
from typing import List, Optional
from bs4 import BeautifulSoup
import httpx
import logging
import pdfplumber

from scraper.config.db import get_pool, init_db, is_downloaded, insert_document
from scraper.models.document import PolicyDocument

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://climatepolicydatabase.org"
POLICIES_URL = f"{BASE_URL}/policies"
DATA_DIR = "scraper/data/policies"

# Concurrency limit for HTTP requests
MAX_CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def download_file(url: str, dest_path: str, client: httpx.AsyncClient) -> bool:
    """Downloads a file asynchronously and validates it is not 0 bytes.
    
    Args:
        url: The URL of the file to download.
        dest_path: The local path to save the file.
        client: The httpx AsyncClient.
        
    Returns:
        True if download was successful and file is valid, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        async with client.stream("GET", url, follow_redirects=True) as response:
            if response.status_code != 200:
                logger.error(f"Failed to download {url}: Status {response.status_code}")
                return False
            
            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    
        # Validate file size
        if os.path.getsize(dest_path) == 0:
            logger.error(f"Downloaded file is 0 bytes: {dest_path}")
            os.remove(dest_path)
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF file using pdfplumber.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        Extracted text content as a string.
    """
    text_content = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        
    return "\n\n".join(text_content)

def get_max_pages(html: str) -> int:
    """Parses the list page HTML to find the total number of pages."""
    soup = BeautifulSoup(html, "html.parser")
    # Find the "Last" page link, e.g., <li class="pager__item--last"><a href="?page=336">
    last_page_link = soup.select_one("li.pager__item--last a, li.pager__item.pager__item--last a")
    
    if last_page_link and last_page_link.has_attr("href"):
        href = last_page_link["href"]
        match = re.search(r"page=(\d+)", href)
        if match:
            return int(match.group(1))
            
    # Fallback: find the highest number in standard pager items if "Last" is missing
    pager_links = soup.select("li.pager__item a")
    max_page = 0
    for link in pager_links:
        href = link.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            max_page = max(max_page, int(match.group(1)))
            
    return max_page

def extract_policy_links(html: str) -> List[str]:
    """Extracts policy detail URLs from a list page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    
    # As per spec: td.views-field-title a
    for a_tag in soup.select("td.views-field-title a"):
        href = a_tag.get("href")
        if href:
            # Ensure it's an absolute URL
            if href.startswith("/"):
                links.append(f"{BASE_URL}{href}")
            else:
                links.append(href)
                
    return links

def extract_pdf_link(html: str) -> Optional[str]:
    """Extracts the 'Source of reference' PDF URL from a detail page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Look for the label "Source of reference"
    labels = soup.find_all("div", class_="field__label")
    for label in labels:
        if "Source of reference" in label.get_text(strip=True):
            # The next sibling or parent structure usually contains the value
            parent = label.find_parent("div")
            if parent:
                value_div = parent.find("div", class_="field__value")
                if value_div:
                    a_tag = value_div.find("a")
                    if a_tag and a_tag.has_attr("href"):
                        return a_tag["href"]
                        
            # Alternative DOM structure: label and value are siblings
            next_sibling = label.find_next_sibling("div", class_="field__value")
            if next_sibling:
                a_tag = next_sibling.find("a")
                if a_tag and a_tag.has_attr("href"):
                    return a_tag["href"]
                    
    return None

async def process_policy(policy_url: str, client: httpx.AsyncClient, pool) -> None:
    """Processes a single policy URL: check DB, fetch detail, download PDF, extract text, insert to DB."""
    async with semaphore:
        if await is_downloaded(pool, policy_url):
            logger.info(f"Skipping already processed policy: {policy_url}")
            return

        logger.info(f"Processing policy: {policy_url}")
        try:
            response = await client.get(policy_url)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"Failed to fetch policy page {policy_url}: {e}")
            return

        pdf_url = extract_pdf_link(html)
        if not pdf_url:
            logger.warning(f"No PDF reference found for {policy_url}")
            return
            
        # Ensure pdf_url is absolute
        if pdf_url.startswith("/"):
            pdf_url = f"{BASE_URL}{pdf_url}"

        # Determine file path
        slug = policy_url.rstrip('/').split('/')[-1]
        file_path = os.path.join(DATA_DIR, f"{slug}.pdf")

        # Download the file
        logger.info(f"Downloading PDF: {pdf_url}")
        success = await download_file(pdf_url, file_path, client)
        if not success:
            logger.error(f"Skipping DB insertion for {policy_url} due to download failure.")
            return

        # Extract text
        logger.info(f"Extracting text from: {file_path}")
        # Run CPU-bound extraction in a thread pool to avoid blocking the event loop
        content = await asyncio.to_thread(extract_text_from_pdf, file_path)
        
        if not content.strip():
            logger.warning(f"Extracted empty text for {file_path}")

        # Extract title from URL slug as fallback, or parse it properly
        title = slug.replace("-", " ").title()

        doc = PolicyDocument(
            title=title,
            source_url=policy_url, # Using policy URL as source_url to track the policy page
            file_path=file_path,
            content=content
        )

        # Insert into DB
        await insert_document(pool, doc)
        logger.info(f"Successfully processed and stored: {policy_url}")

async def crawl():
    """Main crawler entry point."""
    logger.info("Initializing database...")
    pool = await get_pool()
    try:
        await init_db(pool)
    except Exception as e:
        logger.error(f"Failed to initialize database (is Postgres running?): {e}")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Configure httpx client with timeouts and reasonable limits
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        # 1. Fetch the first page to determine max pages
        logger.info(f"Fetching base URL: {POLICIES_URL}")
        try:
            response = await client.get(POLICIES_URL)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"Failed to fetch base URL: {e}")
            return

        max_pages = get_max_pages(html)
        if max_pages == 0:
            logger.warning("Could not determine max pages, defaulting to 1.")
            max_pages = 1
        
        logger.info(f"Found {max_pages} total pages to crawl.")

        # 2. Iterate through all pages
        # For testing purposes, you might want to limit this range.
        for page_num in range(max_pages + 1):
            page_url = f"{POLICIES_URL}?page={page_num}"
            logger.info(f"Fetching list page {page_num}: {page_url}")
            
            try:
                list_response = await client.get(page_url)
                list_response.raise_for_status()
                list_html = list_response.text
            except Exception as e:
                logger.error(f"Failed to fetch list page {page_url}: {e}")
                continue

            # 3. Extract policy URLs
            policy_urls = extract_policy_links(list_html)
            logger.info(f"Found {len(policy_urls)} policies on page {page_num}.")

            # 4. Process each policy concurrently
            tasks = [process_policy(url, client, pool) for url in policy_urls]
            await asyncio.gather(*tasks)

    # Close DB pool
    await pool.close()
    logger.info("Crawl completed.")

if __name__ == "__main__":
    asyncio.run(crawl())
