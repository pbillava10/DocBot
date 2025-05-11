from django.shortcuts import render, redirect
from .your_backend import query_documents, extract_text
import re
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import datetime

# Optional: Enable for Windows
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# This function formats the answer as a paragraph, bullets, or a mix, depending on length and content
# - 1-2 points: paragraph
# - >8 points: summary paragraph + bullets
# - else: bullets

def beautify_answer(text):
    if not isinstance(text, str):
        return ""
    # Split into sentences/points
    points = re.split(r'\.\s+|\n+', text.strip())
    bullet_points = [p.strip() for p in points if len(p.strip()) > 5]
    # If only 1-2 points, show as paragraph
    if len(bullet_points) <= 2:
        para = ' '.join(bullet_points)
        if not para.endswith('.'):
            para += '.'
        return f'<p>{para}</p>'
    # If answer is long, show a summary paragraph (first 1-2 points) then bullets
    if len(bullet_points) > 8:
        summary = ' '.join(bullet_points[:2])
        if not summary.endswith('.'):
            summary += '.'
        html = f'<p>{summary}</p><ul>'
        for point in bullet_points[2:10]:
            if not point.endswith('.'):
                point += '.'
            html += f'<li>{point}</li>'
        html += '</ul>'
        return html
    # Otherwise, show as bullets
    html = '<ul>'
    for point in bullet_points:
        if not point.endswith('.'):
            point += '.'
        html += f'<li>{point}</li>'
    html += '</ul>'
    return html

# Main view for the Q&A assistant

def index(request):
    answers = {}
    citations = {}
    question = ""
    source_titles = []
    uploaded_filenames = request.session.get("uploaded_files", [])
    uploaded_files_display = uploaded_filenames
    history = request.session.get("history", [])
    sources = {}  # Ensure sources is always defined
    error_message = ""
    chat_history = []
    selected_files = []

    if request.method == "POST":
        action = request.POST.get("action")
        # Handle file deletion
        if action == "delete_files":
            for filename in request.session.get("uploaded_files", []):
                file_path = os.path.join("media", filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"[ERROR deleting {filename}]: {e}")
            request.session["uploaded_files"] = []
            request.session.modified = True
            return redirect("home")
        # Handle chat clearing
        elif action == "clear_chat":
            request.session["history"] = []
            request.session["chat_history"] = []
            request.session.modified = True
            return redirect("home")
        # Handle single Q deletion (if implemented)
        elif action == "delete":
            to_delete = request.POST.get("delete_question")
            if to_delete in history:
                history.remove(to_delete)
                request.session["history"] = history
                request.session.modified = True
            return redirect("home")

        question = request.POST.get("question", "").strip()
        uploaded_files = request.FILES.getlist("documents")
        uploaded_filenames = []

        # Save new uploads
        for f in uploaded_files:
            filename = f.name
            file_path = os.path.join("media", filename)
            with open(file_path, 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            uploaded_filenames.append(filename)

        # Update session with combined list
        if uploaded_filenames:
            combined_files = set(request.session.get("uploaded_files", []) + uploaded_filenames)
            request.session["uploaded_files"] = list(combined_files)
            request.session.modified = True
            uploaded_files_display = list(combined_files)

        # Get selected filenames from POST
        selected_files = request.POST.getlist("selected_files")
        texts_with_sources = {}

        # Only include selected files
        for filename in selected_files:
            file_path = os.path.join("media", filename)
            if os.path.exists(file_path):
                try:
                    text = extract_text(file_path)
                    if text.strip():
                        texts_with_sources[filename] = text.strip()
                except Exception as e:
                    print(f"[ERROR extracting from {filename}]: {e}")

        # Show error if no files selected
        if question and not selected_files:
            error_message = "Please select at least one document."
        # Proceed to query if files and question are present
        elif question and texts_with_sources:
            raw_answers, grouped_citations, source_titles = query_documents(question, texts_with_sources)
            print(f"\n[LLM RESPONSE]\n{raw_answers}\n{'=' * 50}")

            answers = {file: beautify_answer(ans) for file, ans in raw_answers.items()}
            single_citation = {file: [snippets[0]] if snippets else [] for file, snippets in grouped_citations.items()}
            # Pass the source_titles for each file (if available)
            sources = {file: source_titles[i] if i < len(source_titles) else '' for i, file in enumerate(answers.keys())}
            citations = single_citation

            # Save question history
            if "history" not in request.session:
                request.session["history"] = []
            request.session["history"].append(question)
            request.session.modified = True
            history = request.session["history"]
            # Save chat history for UI
            if "chat_history" not in request.session:
                request.session["chat_history"] = []
            request.session["chat_history"].append({
                "question": question,
                "answers": answers,
                "citations": citations,
                "sources": sources,
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            request.session.modified = True
            chat_history = request.session["chat_history"]
    else:
        chat_history = request.session.get("chat_history", [])

    return render(request, "index.html", {
        "answers": answers,
        "citations": citations,
        "question": question,
        "uploaded_files": uploaded_files_display,
        "source_titles": sources,
        "history": list(reversed(history)),
        "error_message": error_message,
        "chat_history": chat_history,
        "selected_files": selected_files,
    })
