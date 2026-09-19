import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from backend.utils.logger import logger
from backend.memory.database import SessionLocal, engine
from backend.memory.models import Base
from backend.memory.vector_store import text_to_vector, cosine_similarity, compute_hybrid_score
from backend.knowledge.models import (
    DocumentSource,
    DocumentChunk,
    CitationItem,
    RAGQueryResponse,
    DocumentIndexRequest
)
from backend.knowledge.parser import extract_text_from_file, chunk_text
from backend.config import settings

VAULT_DIR = Path(__file__).parent.parent.parent / "knowledge_vault"

class KnowledgeEngine:
    """
    Personal Knowledge & RAG Engine for JARVIS (Version 9).
    Provides document parsing, semantic vector chunking, hybrid retrieval,
    and LLM augmented question answering over resumes, projects, notes, and documentation.
    """

    def __init__(self):
        # Create database tables for documents and chunks if not present
        Base.metadata.create_all(bind=engine)
        self._ensure_knowledge_vault()

    def _ensure_knowledge_vault(self):
        """Scans and indexes seed documents in knowledge_vault directory on startup."""
        if not VAULT_DIR.exists():
            VAULT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.scan_vault(str(VAULT_DIR))
        except Exception as e:
            logger.warning(f"Initial knowledge vault scan warning: {e}")

    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all indexed knowledge documents."""
        with SessionLocal() as db:
            query = db.query(DocumentSource)
            if category and category.lower() != "all":
                query = query.filter(DocumentSource.category == category.lower())
            docs = query.order_by(DocumentSource.indexed_at.desc()).all()
            return [doc.to_dict() for doc in docs]

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Returns document details and its chunks."""
        with SessionLocal() as db:
            doc = db.query(DocumentSource).filter(DocumentSource.id == doc_id).first()
            if not doc:
                return None
            res = doc.to_dict()
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index).all()
            res["chunks"] = [c.to_dict() for c in chunks]
            return res

    def delete_document(self, doc_id: int) -> bool:
        """Deletes a document and all its chunks from the vector store."""
        with SessionLocal() as db:
            doc = db.query(DocumentSource).filter(DocumentSource.id == doc_id).first()
            if not doc:
                return False
            db.delete(doc)
            db.commit()
            logger.info(f"Deleted document ID {doc_id} ('{doc.title}') from knowledge base.")
            return True

    def index_file(self, file_path: str, category: str = "project", title: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        Parses a document file from disk, chunks it, generates vector embeddings,
        and saves it into SQLite vector memory.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        raw_text, file_type = extract_text_from_file(str(path))
        doc_title = title or path.stem.replace("_", " ").title()
        file_size = path.stat().st_size
        checksum = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        with SessionLocal() as db:
            # Check if document already indexed with same checksum
            existing = db.query(DocumentSource).filter(
                (DocumentSource.file_path == str(path.resolve())) | (DocumentSource.filename == path.name)
            ).first()

            if existing:
                if existing.checksum == checksum and not force:
                    logger.info(f"Document '{path.name}' already indexed and up-to-date.")
                    return existing.to_dict()
                # Update existing
                db.query(DocumentChunk).filter(DocumentChunk.document_id == existing.id).delete()
                doc = existing
                doc.title = doc_title
                doc.file_size = file_size
                doc.checksum = checksum
                doc.file_type = file_type
                doc.category = category
            else:
                doc = DocumentSource(
                    title=doc_title,
                    filename=path.name,
                    file_path=str(path.resolve()),
                    file_type=file_type,
                    category=category,
                    file_size=file_size,
                    checksum=checksum
                )
                db.add(doc)
                db.flush()

            # Split text into overlapping chunks
            chunks_data = chunk_text(raw_text)
            for idx, c in enumerate(chunks_data):
                chunk_embed_text = f"{doc_title} {c['content']}"
                vec = text_to_vector(chunk_embed_text)
                meta = {"header": c.get("header", ""), "length": c.get("length", 0)}
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=c["content"],
                    vector_json=json.dumps(vec.tolist()),
                    token_count=len(c["content"].split()),
                    metadata_json=json.dumps(meta)
                )
                db.add(chunk_obj)

            doc.total_chunks = len(chunks_data)
            db.commit()
            db.refresh(doc)
            logger.info(f"Indexed document '{doc.title}' ({doc.filename}) into {len(chunks_data)} chunks.")
            return doc.to_dict()

    def index_text(self, title: str, content: str, category: str = "notes", filename: Optional[str] = None) -> Dict[str, Any]:
        """Indexes raw text directly into the knowledge base."""
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        fname = filename or f"{title.lower().replace(' ', '_')}.md"

        with SessionLocal() as db:
            existing = db.query(DocumentSource).filter(DocumentSource.title == title).first()
            if existing:
                db.query(DocumentChunk).filter(DocumentChunk.document_id == existing.id).delete()
                doc = existing
                doc.checksum = checksum
                doc.category = category
                doc.file_size = len(content.encode('utf-8'))
            else:
                doc = DocumentSource(
                    title=title,
                    filename=fname,
                    file_path=None,
                    file_type="markdown",
                    category=category,
                    file_size=len(content.encode('utf-8')),
                    checksum=checksum
                )
                db.add(doc)
                db.flush()

            chunks_data = chunk_text(content)
            for idx, c in enumerate(chunks_data):
                vec = text_to_vector(c["content"])
                meta = {"header": c.get("header", "")}
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=c["content"],
                    vector_json=json.dumps(vec.tolist()),
                    token_count=len(c["content"].split()),
                    metadata_json=json.dumps(meta)
                )
                db.add(chunk_obj)

            doc.total_chunks = len(chunks_data)
            db.commit()
            db.refresh(doc)
            return doc.to_dict()

    def scan_vault(self, vault_path: Optional[str] = None, force: bool = False) -> List[Dict[str, Any]]:
        """Scans a directory on the laptop and indexes all valid documents."""
        folder = Path(vault_path) if vault_path else VAULT_DIR
        if not folder.exists():
            return []

        indexed = []
        supported_exts = {".md", ".markdown", ".txt", ".pdf", ".py", ".json", ".rst"}
        
        for file in folder.rglob("*"):
            if file.is_file() and file.suffix.lower() in supported_exts:
                # Infer category from filename or folder
                fname = file.stem.lower()
                cat = "project"
                if "project" in fname:
                    cat = "project"
                elif fname.startswith("resume") or "cv" in fname:
                    cat = "resume"
                elif "note" in fname:
                    cat = "notes"
                elif "doc" in fname or "manual" in fname:
                    cat = "documentation"
                elif file.suffix.lower() == ".pdf":
                    cat = "pdf"

                try:
                    res = self.index_file(str(file), category=cat, force=force)
                    indexed.append(res)
                except Exception as e:
                    logger.error(f"Failed to index vault file '{file.name}': {e}")

        logger.info(f"Scanned vault at '{folder}'. Processed {len(indexed)} documents.")
        return indexed

    def search_chunks(self, query: str, category: Optional[str] = None, top_k: int = 4) -> List[CitationItem]:
        """
        Retrieves the top-K most relevant document chunks for a query
        using dense vector embeddings and hybrid keyword ranking.
        """
        if not query or not query.strip():
            return []

        query_vec = text_to_vector(query)
        scored_candidates: List[Tuple[float, DocumentChunk, DocumentSource]] = []

        with SessionLocal() as db:
            doc_query = db.query(DocumentSource)
            if category and category.lower() != "all":
                doc_query = doc_query.filter(DocumentSource.category == category.lower())
            docs = {d.id: d for d in doc_query.all()}

            if not docs:
                return []

            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(docs.keys())).all()

            for chunk in chunks:
                doc = docs.get(chunk.document_id)
                if not doc:
                    continue

                chunk_vec = None
                if chunk.vector_json:
                    try:
                        chunk_vec = json.loads(chunk.vector_json)
                    except Exception:
                        pass

                score = compute_hybrid_score(
                    query=query,
                    query_vec=query_vec,
                    doc_key=f"{doc.title} {doc.filename}",
                    doc_content=chunk.content,
                    doc_tags=doc.category,
                    doc_vec=chunk_vec
                )

                if score > 0.05:
                    scored_candidates.append((score, chunk, doc))

        # Sort by relevance score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = scored_candidates[:top_k]

        citations = []
        for score, chunk, doc in top_candidates:
            # Create a concise excerpt
            excerpt = chunk.content[:240].strip() + ("..." if len(chunk.content) > 240 else "")
            citations.append(CitationItem(
                document_id=doc.id,
                title=doc.title,
                filename=doc.filename,
                category=doc.category,
                chunk_index=chunk.chunk_index,
                relevance_score=round(float(score), 3),
                excerpt=excerpt
            ))

        return citations

    def synthesize_local_answer(self, query: str, citations: List[CitationItem]) -> str:
        """
        Builds a useful answer from retrieved chunks when the cloud LLM is slow,
        unavailable, or unnecessary. This keeps RAG responsive offline.
        """
        if not citations:
            return (
                "I couldn't find matching material in your personal knowledge vault. "
                "Add or rescan documents and I can search them."
            )

        query_lower = query.lower()
        wants_technology = any(
            term in query_lower
            for term in ("technology", "technologies", "tech stack", "stack", "tools", "used")
        )

        with SessionLocal() as db:
            source_blocks = []
            for c in citations:
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == c.document_id,
                    DocumentChunk.chunk_index == c.chunk_index
                ).first()
                if chunk:
                    source_blocks.append((c, chunk.content))

        if not source_blocks:
            top_cite = citations[0]
            return f"Based on **{top_cite.title}** ({top_cite.filename}): {top_cite.excerpt}"

        if wants_technology:
            tech_keywords = [
                "Python", "FastAPI", "Pydantic", "Uvicorn", "Groq", "LangChain",
                "FAISS", "SentenceTransformers", "PyPDF2", "pdfplumber",
                "python-docx", "React", "Vite", "TailwindCSS", "Lucide",
                "PostgreSQL", "Redis", "Docker", "Docker Compose", "GitHub Actions"
            ]
            found = []
            combined = "\n".join(content for _, content in source_blocks)
            for keyword in tech_keywords:
                if keyword.lower() in combined.lower() and keyword not in found:
                    found.append(keyword)

            if found:
                cite = source_blocks[0][0]
                return (
                    f"From **{cite.title}** ({cite.filename}), the project uses: "
                    f"{', '.join(found)}."
                )

        excerpt_lines = []
        for cite, content in source_blocks[:2]:
            clean = " ".join(content.split())
            if len(clean) > 420:
                clean = clean[:420].rsplit(" ", 1)[0] + "..."
            excerpt_lines.append(f"From **{cite.title}** ({cite.filename}): {clean}")

        return "\n\n".join(excerpt_lines)

    async def query_rag(self, query: str, category: Optional[str] = None, top_k: int = 4) -> RAGQueryResponse:
        """
        Executes the full RAG pipeline:
        Question -> Embedding -> Hybrid Search -> Top Chunks -> Prompt Synthesis -> Groq LLM -> Response with Citations.
        """
        logger.info(f"[KnowledgeEngine] RAG Query received: '{query}' (category: {category})")
        
        # 1. Retrieve top chunks
        citations = self.search_chunks(query, category=category, top_k=top_k)

        with SessionLocal() as db:
            total_docs = db.query(DocumentSource).count()
            # If citations found, load full chunk contents for synthesis
            chunk_contexts = []
            for c in citations:
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == c.document_id,
                    DocumentChunk.chunk_index == c.chunk_index
                ).first()
                if chunk:
                    chunk_contexts.append(
                        f"--- Source: {c.title} ({c.filename} | Category: {c.category} | Chunk #{c.chunk_index}) ---\n"
                        f"{chunk.content}"
                    )

        if not chunk_contexts:
            return RAGQueryResponse(
                query=query,
                answer="I couldn't find any relevant documents in your personal knowledge vault matching that query. You can add documents or project files to search them.",
                citations=[],
                total_sources_scanned=total_docs
            )

        context_str = "\n\n".join(chunk_contexts)

        # 2. Synthesize answer with Groq LLM
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS Personal Knowledge Assistant. "
                    "Answer the user's question accurately, concisely, and informatively based on the retrieved document excerpts below. "
                    "If the answer is in the documents, state the key facts, technologies, or details clearly. "
                    "Cite the relevant source document name in your answer.\n\n"
                    f"Retrieved Document Passages:\n{context_str}"
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]

        try:
            from backend.ai.client import ai_client
            client = ai_client.get_client()
            llm_resp = await client.chat.completions.create(
                messages=prompt_messages,
                model=settings.llm_model,
                temperature=0.2
            )
            answer_text = llm_resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"LLM RAG synthesis failed, using fallback summary: {e}")
            answer_text = self.synthesize_local_answer(query, citations)

        return RAGQueryResponse(
            query=query,
            answer=answer_text,
            citations=citations,
            total_sources_scanned=total_docs
        )

# Global singleton knowledge engine instance
knowledge_engine = KnowledgeEngine()
