# Project Overview
- Mission: A RAG-based document assistant that scrapes PDFs/docs from specific web targets and provides a chat interface for querying the extracted data.

# Component 1: Web Scraper (Data Ingestion)
- Goal: Idempotent downloading and processing of PDFs.
- Rules:
    - Always check if a file already exists in the local storage before downloading.
    - Standardize metadata: Every entry in the vector DB must include source_url, download_date, and file_type.
    - Cleanup: Implement a logic to remove broken or 0-byte PDFs.
- Style: Prefer asynchronous fetching to handle multiple documents efficiently.

# Component 2: RAG Agent (Chatbot)
- Persona: You are a precise research assistant. You answer only based on the retrieved context from the vector database. 
- Instructions:
    - If the answer is not in the database, explicitly state: "I don't have information on that in the current document set."
    - Always include a "Source" citation in the response (e.g., [Source: document_name.pdf]).
    - Keep responses concise and formatted in Markdown.

## 🛠 Tech Stack
- **Language:** Python
- **Framework:** uv

### Web Scraper Components
- **Libraries:** httpx, beautifulsoup4
- **Concurrency:** asyncio
- **Vector Database:** Supabase (vector/postgres)
- **Parsing:** pdfplumber

### RAG Agent Components
- **Agent Framework:** Google ADK
- **Embeddings:** x-ai/grok-embed-fast:1
- **LLM:** Google Gemini 3 Pro Preview

## 📝 Coding Standards
- Use functional components and hooks.
- Prefer Python for type safety.
- Use 2 spaces for indentation.
- Documentation: Use Google-style docstrings for all functions.
- Error Handling: Use specific exception blocks (e.g., RequestException for the scraper) rather than generic except Exception.
- Follow directory structure: `/agents`, `/tools`, `/models`, `/config`, `/data`, `/scripts`, `/tests`.

## 🚀 Vibe Coding Rules
- **Proactive Documentation:** Update `README.md` and `CHANGELOG.md` with every significant feature.
- **Commit Often:** If using git, propose changes and ask for commit messages.
- **Fail Fast:** If an error occurs, analyze the logs and immediately propose a fix.
- **Iterative Improvement:** Ask for feedback on the code structure periodically.

## 📂 Project Structure
- Ensure all new files follow the convention: `[feature].py`.

## 💡 Preferred Workflow
1. Analyze existing code before generating new code.
2. If uncertain, ask for clarification before writing files.
3. Use Mermaid.js for architecture diagrams in `README.md` when proposing structural changes.
