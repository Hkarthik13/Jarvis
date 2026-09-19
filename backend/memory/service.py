import json
import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import desc

from backend.memory.database import init_db, get_db
from backend.memory.models import MemoryEntry, UserPreference, ConversationHistory, TaskItem
from backend.memory.vector_store import text_to_vector, compute_hybrid_score
from backend.utils.logger import logger

class MemoryService:
    def __init__(self):
        init_db()

    # --- 1. Long-Term Memory & Facts ---
    def save_memory(
        self,
        content: str,
        key: str = "",
        category: str = "fact",
        tags: List[str] = None,
        importance: int = 3
    ) -> Dict[str, Any]:
        """Saves or updates a memory entry with its semantic vector embedding."""
        tags_str = ",".join([t.strip().lower() for t in tags]) if tags else ""
        combined_text = f"{key} {content} {tags_str}".strip()
        vec = text_to_vector(combined_text)
        vec_json = json.dumps(vec.tolist())

        with get_db() as db:
            # Check if an existing memory with same key and category exists
            existing = None
            if key:
                existing = db.query(MemoryEntry).filter(
                    MemoryEntry.category == category,
                    MemoryEntry.key == key
                ).first()

            if existing:
                existing.content = content
                existing.tags = tags_str
                existing.importance = importance
                existing.vector_json = vec_json
                existing.updated_at = datetime.datetime.utcnow()
                db.flush()
                logger.info(f"Updated existing memory: '{key}' in category '{category}'")
                return existing.to_dict()
            else:
                entry = MemoryEntry(
                    category=category,
                    key=key or content[:50],
                    content=content,
                    tags=tags_str,
                    importance=importance,
                    vector_json=vec_json
                )
                db.add(entry)
                db.flush()
                logger.info(f"Saved new memory: '{entry.key}' (Category: {category})")
                return entry.to_dict()

    def recall_memories(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
        threshold: float = 0.10
    ) -> List[Dict[str, Any]]:
        """Searches memories using hybrid vector similarity and keyword ranking."""
        query_vec = text_to_vector(query)
        scored_entries = []

        with get_db() as db:
            q = db.query(MemoryEntry)
            if category:
                q = q.filter(MemoryEntry.category == category)
            all_entries = q.all()

            for entry in all_entries:
                doc_vec = None
                if entry.vector_json:
                    try:
                        doc_vec = np.array(json.loads(entry.vector_json), dtype=np.float32)
                    except Exception:
                        doc_vec = text_to_vector(f"{entry.key} {entry.content}")

                score = compute_hybrid_score(
                    query=query,
                    query_vec=query_vec,
                    doc_key=entry.key or "",
                    doc_content=entry.content or "",
                    doc_tags=entry.tags or "",
                    doc_vec=doc_vec
                )

                if score >= threshold:
                    entry_dict = entry.to_dict()
                    entry_dict["score"] = round(score, 3)
                    scored_entries.append((score, entry_dict))

        # Sort descending by relevance score
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_entries[:top_k]]

    def list_all_memories(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as db:
            q = db.query(MemoryEntry)
            if category:
                q = q.filter(MemoryEntry.category == category)
            return [e.to_dict() for e in q.order_by(desc(MemoryEntry.updated_at)).all()]

    def delete_memory(self, memory_id: int) -> bool:
        with get_db() as db:
            entry = db.query(MemoryEntry).filter(MemoryEntry.id == memory_id).first()
            if entry:
                db.delete(entry)
                logger.info(f"Deleted memory id {memory_id}")
                return True
            return False

    # --- 2. User Preferences ---
    def set_preference(self, key: str, value: str, category: str = "general") -> Dict[str, Any]:
        with get_db() as db:
            clean_key = key.strip().lower()
            pref = db.query(UserPreference).filter(UserPreference.key == clean_key).first()
            if pref:
                pref.value = str(value).strip()
                pref.category = category
                pref.updated_at = datetime.datetime.utcnow()
            else:
                pref = UserPreference(key=clean_key, value=str(value).strip(), category=category)
                db.add(pref)
            db.flush()
            logger.info(f"Set preference '{clean_key}' = '{value}'")
            return pref.to_dict()

    def get_preference(self, key: str) -> Optional[str]:
        with get_db() as db:
            clean_key = key.strip().lower()
            pref = db.query(UserPreference).filter(UserPreference.key == clean_key).first()
            return pref.value if pref else None

    def get_all_preferences(self) -> Dict[str, str]:
        with get_db() as db:
            prefs = db.query(UserPreference).all()
            return {p.key: p.value for p in prefs}

    # --- 3. Task / To-Do Items ---
    def add_task(
        self,
        title: str,
        description: str = "",
        project: str = "General",
        priority: str = "medium",
        due_date: str = ""
    ) -> Dict[str, Any]:
        with get_db() as db:
            task = TaskItem(
                title=title.strip(),
                description=description.strip(),
                project=project.strip() or "General",
                priority=priority.lower().strip() if priority in ("low", "medium", "high", "urgent") else "medium",
                status="pending",
                due_date=due_date.strip()
            )
            db.add(task)
            db.flush()
            logger.info(f"Added task: '{task.title}' under project '{task.project}'")
            return task.to_dict()

    def update_task_status(self, task_id: int, status: str) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            task = db.query(TaskItem).filter(TaskItem.id == task_id).first()
            if task:
                task.status = status.lower().strip()
                if task.status == "completed":
                    task.completed_at = datetime.datetime.utcnow()
                db.flush()
                logger.info(f"Updated task id {task_id} status to '{status}'")
                return task.to_dict()
            return None

    def list_tasks(self, status: Optional[str] = None, project: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as db:
            q = db.query(TaskItem)
            if status:
                q = q.filter(TaskItem.status == status.lower().strip())
            if project:
                q = q.filter(TaskItem.project.ilike(f"%{project.strip()}%"))
            tasks = q.order_by(desc(TaskItem.created_at)).all()
            return [t.to_dict() for t in tasks]

    # --- 4. Conversation History ---
    def save_conversation(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            record = ConversationHistory(
                session_id=session_id,
                role=role,
                content=content,
                metadata_json=json.dumps(metadata or {})
            )
            db.add(record)
            db.flush()
            return record.to_dict()

    def get_conversation_history(self, session_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
        with get_db() as db:
            records = db.query(ConversationHistory).filter(
                ConversationHistory.session_id == session_id
            ).order_by(desc(ConversationHistory.timestamp)).limit(limit).all()
            return [r.to_dict() for r in reversed(records)]

    # --- 5. Context Summary for Prompt Injection ---
    def get_active_context_summary(self) -> str:
        """Builds a condensed context block of user preferences, projects, and active tasks."""
        try:
            prefs = self.get_all_preferences()
            projects = self.list_all_memories(category="project")
            pending_tasks = self.list_tasks(status="pending")[:5]

            lines = []
            if prefs:
                pref_str = ", ".join([f"{k}: {v}" for k, v in prefs.items()])
                lines.append(f"User Preferences: {pref_str}")
            if projects:
                proj_str = "; ".join([f"{p['key']}: {p['content']}" for p in projects[:3]])
                lines.append(f"Known Projects: {proj_str}")
            if pending_tasks:
                task_str = "; ".join([f"[{t['id']}] {t['title']} ({t['project']})" for t in pending_tasks])
                lines.append(f"Pending Tasks: {task_str}")

            if lines:
                return "Active Memory Context:\n" + "\n".join(lines)
            return ""
        except Exception as e:
            logger.error(f"Error generating active context summary: {e}")
            return ""

# Singleton instance
memory_service = MemoryService()
