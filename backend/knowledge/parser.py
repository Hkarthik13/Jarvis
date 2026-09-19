import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.utils.logger import logger

def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """
    Extracts plain text content and detects file type from a given file path.
    Supports: .md, .txt, .pdf, .py, .json, .csv, .yaml, .yml, .rst
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    ext = path.suffix.lower()
    file_type = "text"

    # 1. Markdown & Text files
    if ext in (".md", ".markdown"):
        file_type = "markdown"
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), file_type

    elif ext in (".txt", ".rst", ".log"):
        file_type = "text"
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), file_type

    elif ext in (".py", ".js", ".ts", ".dart", ".html", ".css", ".sql", ".sh"):
        file_type = "code"
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), file_type

    elif ext in (".json", ".yaml", ".yml", ".csv"):
        file_type = "data"
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), file_type

    # 2. PDF Files
    elif ext == ".pdf":
        file_type = "pdf"
        text = _extract_text_from_pdf(path)
        return text, file_type

    # Fallback to general text read
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), "text"
    except Exception as e:
        logger.error(f"Failed to read file '{file_path}': {e}")
        raise ValueError(f"Unsupported or unreadable file format: {ext}")


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts text from PDF using pypdf/pdfminer or a lightweight stream extractor."""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        pages = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"--- Page {idx+1} ---\n{page_text}")
        return "\n\n".join(pages)
    except ImportError:
        pass

    try:
        import pypdf2
        reader = pypdf2.PdfReader(str(pdf_path))
        pages = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"--- Page {idx+1} ---\n{page_text}")
        return "\n\n".join(pages)
    except ImportError:
        pass

    # Fallback basic PDF text stream regex extractor
    try:
        with open(pdf_path, "rb") as f:
            raw = f.read()
        # Extract stream objects
        streams = re.findall(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw, re.DOTALL)
        extracted = []
        for stream in streams:
            try:
                # Try simple latin1/utf-8 decode or ascii filter
                clean = re.sub(r"[^\x20-\x7E\n]", " ", stream.decode("latin1", errors="ignore"))
                if len(clean.strip()) > 30:
                    extracted.append(clean.strip())
            except Exception:
                continue
        if extracted:
            return "\n\n".join(extracted)
    except Exception as e:
        logger.warning(f"Fallback PDF parsing encountered error: {e}")

    return f"PDF document indexed from: {pdf_path.name}"


def chunk_text(
    text: str,
    chunk_size: int = 650,
    overlap: int = 120,
    min_chunk_size: int = 80
) -> List[Dict[str, Any]]:
    """
    Splits text into semantically cohesive overlapping chunks.
    Preserves markdown headers, paragraphs, and sentence boundaries.
    """
    if not text or not text.strip():
        return []

    # Clean whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split primarily on paragraphs / double newlines
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    current_header = ""

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Track markdown headers (e.g. # Title, ## Section)
        header_match = re.match(r"^(#{1,6}\s+.+)", para_clean)
        if header_match:
            current_header = header_match.group(1)

        # If adding paragraph exceeds chunk_size, save current chunk and roll over
        if len(current_chunk) + len(para_clean) > chunk_size and len(current_chunk) >= min_chunk_size:
            chunk_content = current_chunk.strip()
            if current_header and not chunk_content.startswith("#"):
                chunk_content = f"{current_header}\n\n{chunk_content}"
            chunks.append({
                "content": chunk_content,
                "header": current_header,
                "length": len(chunk_content)
            })
            # Overlap: keep the last `overlap` characters from the previous chunk
            overlap_prefix = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_prefix + "\n\n" + para_clean
        else:
            if current_chunk:
                current_chunk += "\n\n" + para_clean
            else:
                current_chunk = para_clean

    # Add final remaining chunk
    if len(current_chunk.strip()) >= min_chunk_size:
        chunk_content = current_chunk.strip()
        if current_header and not chunk_content.startswith("#"):
            chunk_content = f"{current_header}\n\n{chunk_content}"
        chunks.append({
            "content": chunk_content,
            "header": current_header,
            "length": len(chunk_content)
        })
    elif chunks and len(current_chunk.strip()) > 0:
        # Append small remnant to last chunk
        chunks[-1]["content"] += "\n\n" + current_chunk.strip()
        chunks[-1]["length"] = len(chunks[-1]["content"])
    elif not chunks and len(current_chunk.strip()) > 0:
        chunks.append({
            "content": current_chunk.strip(),
            "header": current_header,
            "length": len(current_chunk.strip())
        })

    return chunks
