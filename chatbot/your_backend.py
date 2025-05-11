import os
import fitz  # PyMuPDF
import pandas as pd
import pytesseract
from PIL import Image
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_together import Together
from langchain_core.prompts import PromptTemplate
import time
from collections import defaultdict
import pickle

# Set Together.ai API Key for LLM
os.environ["TOGETHER_API_KEY"] = "18f47b078c6565de08412d0acdc7f4129254cb196beb728f36ec0002bea3c0a8"

# Directory for caching document embeddings
EMBEDDING_CACHE_DIR = os.path.join("media", "embeddings")
os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)

def get_embedding_cache_path(filename):
    """Return the cache path for a given filename's embeddings."""
    return os.path.join(EMBEDDING_CACHE_DIR, f"{filename}.pkl")

# Extract text from various file types
# Supports: PDF, DOCX, CSV, TXT, PNG/JPG/JPEG (OCR)
def extract_text(file_path):
    ext = file_path.lower().split('.')[-1]
    try:
        if ext == 'pdf':
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text("text") for page in doc)
            # If PDF is image-based, use OCR
            if not text.strip():
                text = ""
                for page_num in range(len(doc)):
                    pix = doc[page_num].get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text += pytesseract.image_to_string(img)
            return text
        elif ext == 'docx':
            return "\n".join(p.text for p in Document(file_path).paragraphs)
        elif ext == 'csv':
            return pd.read_csv(file_path).to_string(index=False)
        elif ext in ['png', 'jpg', 'jpeg']:
            return pytesseract.image_to_string(Image.open(file_path))
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    except Exception as e:
        return f"[Error reading file: {str(e)}]"

# Get or create (and cache) embeddings for a document
# Uses FAISS for vector storage and HuggingFace for embeddings
def get_or_create_embeddings(filename, content, embedder):
    cache_path = get_embedding_cache_path(filename)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                vectordb = pickle.load(f)
            return vectordb
        except Exception as e:
            print(f"[Embedding cache load error for {filename}]: {e}")
    # Compute and cache embeddings if not found
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    split_chunks = splitter.split_text(content)
    metadatas = [{"source": filename}] * len(split_chunks)
    vectordb = FAISS.from_texts(split_chunks, embedder, metadatas=metadatas)
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(vectordb, f)
    except Exception as e:
        print(f"[Embedding cache save error for {filename}]: {e}")
    return vectordb

# Main QnA logic: retrieves relevant chunks, runs LLM, and returns answers/citations
def query_documents(question, texts_with_sources):
    embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordbs = {}
    # Build or load vector DB for each file
    for filename, content in texts_with_sources.items():
        vectordb = get_or_create_embeddings(filename, content, embedder)
        vectordbs[filename] = vectordb
    # Retrieve relevant docs from all files
    all_docs = []
    all_metadatas = []
    for filename, vectordb in vectordbs.items():
        docs = vectordb.similarity_search(question, k=10)
        all_docs.extend(docs)
        all_metadatas.extend([{"source": filename}] * len(docs))
    if not all_docs:
        return "No relevant information found in uploaded documents.", [], []
    # Prompt for the LLM
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are an expert assistant. Based ONLY on the following CONTEXT, give a detailed, helpful answer to the QUESTION below.
Use complete sentences, explain clearly, and include specific insights when possible.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""
    )
    llm = Together(model="mistralai/Mistral-7B-Instruct-v0.1", temperature=0.3, max_tokens=512)
    # Combine all doc contents for context
    combined_context = "\n".join([doc.page_content for doc in all_docs])
    # Directly call the LLM with the combined context and question
    prompt = prompt_template.format(context=combined_context, question=question)
    response = llm.invoke(prompt).strip()
    # For compatibility, create a fake answers_by_file and grouped_citations
    answers_by_file = {}
    grouped_citations = defaultdict(list)
    for doc in all_docs:
        source = doc.metadata.get("source", "Unknown")
        snippet = doc.page_content.strip().replace("\n", " ")[:300] + "..."
        grouped_citations[source].append(snippet)
        # Only set the answer for the first doc per file
        if source not in answers_by_file:
            answers_by_file[source] = response
    return answers_by_file, dict(grouped_citations), list(answers_by_file.keys())
