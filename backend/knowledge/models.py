import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.memory.models import Base

# --- SQLAlchemy ORM Models ---

class DocumentSource(Base):
    """
    Represents an indexed document file (e.g. Resume, Project documentation, PDF, Notes).
    """
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), default="markdown", index=True)  # pdf, markdown, txt, code, docx
    category = Column(String(50), default="project", index=True)   # resume, project, notes, pdf, documentation, general
    file_size = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    indexed_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "category": self.category,
            "file_size": self.file_size,
            "total_chunks": self.total_chunks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None
        }


class DocumentChunk(Base):
    """
    Represents an individual text passage chunk with its dense embedding vector.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_json = Column(Text, nullable=True)  # JSON-serialized embedding vector
    token_count = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")  # header, section, page_number
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("DocumentSource", back_populates="chunks")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "token_count": self.token_count,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# --- Pydantic Schemas ---

class CitationItem(BaseModel):
    document_id: int
    title: str
    filename: str
    category: str
    chunk_index: int
    relevance_score: float
    excerpt: str

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="User question or search query")
    category: Optional[str] = Field(default=None, description="Optional category filter (resume, project, notes, pdf, documentation)")
    top_k: int = Field(default=4, description="Number of top chunks to retrieve")

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem] = Field(default_factory=list)
    total_sources_scanned: int = 0

class DocumentIndexRequest(BaseModel):
    file_path: Optional[str] = Field(default=None, description="Absolute or relative path to document file")
    title: Optional[str] = Field(default=None, description="Optional title")
    content: Optional[str] = Field(default=None, description="Direct text content if not using file path")
    category: str = Field(default="project", description="Category: resume, project, notes, pdf, documentation")
