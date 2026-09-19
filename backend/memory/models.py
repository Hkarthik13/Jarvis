import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MemoryEntry(Base):
    """
    Stores long-term facts, project descriptions, notes, and general knowledge.
    Categories: 'fact', 'project', 'note', 'preference', 'general'.
    """
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), default="fact", index=True)
    key = Column(String(150), index=True)  # Title / Topic / Key identifier
    content = Column(Text, nullable=False)
    tags = Column(String(255), default="")  # Comma-separated tags
    importance = Column(Integer, default=3)  # Scale: 1 (low) to 5 (critical)
    vector_json = Column(Text, nullable=True)  # JSON-serialized embedding vector
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "key": self.key,
            "content": self.content,
            "tags": self.tags.split(",") if self.tags else [],
            "importance": self.importance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserPreference(Base):
    """
    Key-Value store for user preferences (e.g., name, tone, dev language, wake word).
    """
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ConversationHistory(Base):
    """
    Stores past conversation turns between user and JARVIS for session persistence.
    """
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), default="default", index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class TaskItem(Base):
    """
    Stores tasks, to-dos, and project action items.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    project = Column(String(100), default="General", index=True)
    priority = Column(String(20), default="medium")  # 'low', 'medium', 'high', 'urgent'
    status = Column(String(20), default="pending", index=True)  # 'pending', 'in_progress', 'completed'
    due_date = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
