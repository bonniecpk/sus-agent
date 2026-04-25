# Specification: Climate Policy Web Crawler

## Goal
Build an idempotent web crawler that scrapes climate policies from `https://climatepolicydatabase.org/policies`, follows each policy link, and downloads the PDF linked in the "Source of reference" section.

## Target
- **Base URL:** `https://climatepolicydatabase.org/policies`
- **Sample Detail URL:** `https://climatepolicydatabase.org/policies/eu-climate-change-law-amendment`

## Technical Requirements
- **Language:** Python
- **Framework:** `httpx` for requests, `beautifulsoup4` for parsing.
- **Concurrency:** `asyncio` for efficient crawling.
- **Storage:** PDFs should be saved in `data/policies/`.
- **Idempotency:** Skip downloading if the file already exists or has been processed.
- **Metadata:** Store a mapping of policy name to source URL and local file path.

## Implementation Details

### 1. Navigation & Pagination
- The crawler starts at `https://climatepolicydatabase.org/policies`.
- It identifies the total number of pages from the "Last" page link (`?page=336`).
- It iterates through all pages using the `?page=N` query parameter.

### 2. Data Extraction
- **List Page:** Extract all links matching `td.views-field-title a`.
- **Detail Page:**
    - Extract the policy title.
    - Locate the "Source of reference" field.
    - Extract the `href` attribute from the anchor tag within the corresponding `.field__value`.

### 3. File Processing
- Standardize filenames based on the policy slug (e.g., `eu-climate-change-law-amendment.pdf`).
- Download PDFs only if they don't already exist in the local storage.
- Log successes and failures.

### 4. Error Handling
- Handle network timeouts and connection errors using `httpx`.
- Gracefully handle cases where "Source of reference" might be missing or not a PDF.

## Proposed Structure
- `web-scrapper/climate_crawler.py`: Main crawler logic.
- `data/policies/`: Destination for downloaded PDFs.
- `data/metadata.json`: JSON file tracking downloaded policies.
