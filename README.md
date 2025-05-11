# Document Q&A Assistant

A Django-based web application that allows users to upload documents (PDF, DOCX, CSV, TXT, images) and ask questions about their content using advanced language models and vector search.

## Features
- Upload multiple document types: PDF, DOCX, CSV, TXT, PNG, JPG, JPEG
- Ask questions and get context-aware answers
- Caches document embeddings for fast repeated queries
- Maintains a scrollable chat history with timestamps
- Collapsible citations and source display for each answer
- User-friendly, modern UI

## Setup & Installation

1. **Clone the repository**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```  
3. **Install Tesseract OCR** (for image/PDF OCR)
   - Windows: Download from https://github.com/tesseract-ocr/tesseract
   - Linux: `sudo apt-get install tesseract-ocr`
4. **Add Your Together AI API Key** in chatbot/your_backend.py
4. **Run migrations**
   ```bash
   python manage.py migrate
   ```
5. **Start the server**
   ```bash
   python manage.py runserver
   ```
6. **Open your browser** and go to `http://127.0.0.1:8000/`

## Project Structure & File Purpose

- `manage.py` — Django's command-line utility for running the project
- `requirements.txt` — All Python dependencies
- `README.md` — This file
- `db.sqlite3` — SQLite database (auto-created)
- `media/` — Uploaded files and cached embeddings
- `temp/` — (Optional) Temporary files

### Main Django Apps

#### `docbot/`
- `settings.py` — Django project settings
- `urls.py` — Main URL routing
- `asgi.py` — ASGI config for async deployment
- `wsgi.py` — WSGI config for web server deployment
- `__init__.py` — Marks as Python package

#### `chatbot/`
- `views.py` — Main view logic for QnA, file upload, chat history, etc.
- `your_backend.py` — Text extraction, embedding, and QnA logic (LLM, vector search, caching)
- `templates/index.html` — Main HTML template (UI)
- `templatetags/get_item.py` — Custom template filter for dictionary access in templates
- `admin.py` — (Boilerplate) Django admin config
- `apps.py` — Django app config
- `migrations/` — Django migration files (empty unless you add models)
- `__init__.py` — Marks as Python package

## Usage
- Upload one or more documents
- Select which documents to use for QnA
- Ask a question in the input box
- View answers, citations, and sources in the chat history
- Use "Delete All Files" to remove all uploaded files
- Use "Clear Chat" to clear the chat history

## Notes
- Embeddings are cached in `media/embeddings/` for fast repeated queries
- For best OCR results, ensure Tesseract is installed and in your PATH
- Large files may take longer to process on first upload (subsequent queries are fast)

## License
MIT 