from typing import Any, Dict, List
from backend.ai.registry import BaseTool, registry
from backend.memory.service import memory_service
from backend.utils.logger import logger


class RememberFactTool(BaseTool):
    @property
    def name(self) -> str:
        return "remember_fact"

    @property
    def description(self) -> str:
        return "Stores important user facts, project descriptions, notes, or preferences in long-term memory."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The exact fact, note, or information to remember (e.g. 'My main project is Digital Behaviour Twin')."
                        },
                        "key": {
                            "type": "string",
                            "description": "Short title or key identifier (e.g. 'main_project', 'favorite_color', 'api_convention')."
                        },
                        "category": {
                            "type": "string",
                            "enum": ["fact", "project", "note", "preference", "general"],
                            "description": "Category of the information to store."
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional search tags or keywords."
                        }
                    },
                    "required": ["content"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        content = args.get("content")
        if not content or not str(content).strip():
            raise ValueError("Parameter 'content' is required.")
        key = args.get("key", "").strip()
        category = args.get("category", "fact").strip().lower()
        if category not in ("fact", "project", "note", "preference", "general"):
            category = "fact"
        tags = args.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        return {
            "content": str(content).strip(),
            "key": key or str(content)[:40].strip(),
            "category": category,
            "tags": tags
        }

    def execute(self, args: Dict[str, Any]) -> Any:
        content = args["content"]
        key = args["key"]
        category = args["category"]
        tags = args["tags"]
        
        entry = memory_service.save_memory(
            content=content,
            key=key,
            category=category,
            tags=tags
        )
        return f"Successfully remembered: '{entry['key']}' in category '{entry['category']}'. Content: {entry['content']}"


class RecallMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "recall_memory"

    @property
    def description(self) -> str:
        return "Searches and retrieves relevant memories, facts, project details, and notes from long-term memory."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query or question to retrieve matching memories for."
                        },
                        "category": {
                            "type": "string",
                            "enum": ["all", "fact", "project", "note", "preference", "general"],
                            "description": "Optional category filter."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query")
        if not query or not str(query).strip():
            raise ValueError("Parameter 'query' is required.")
        cat = args.get("category", "all").strip().lower()
        if cat == "all" or cat not in ("fact", "project", "note", "preference", "general"):
            cat = None
        return {"query": str(query).strip(), "category": cat}

    def execute(self, args: Dict[str, Any]) -> Any:
        query = args["query"]
        category = args["category"]
        results = memory_service.recall_memories(query=query, category=category, top_k=5)
        
        if not results:
            return f"No memories found matching '{query}'."
            
        formatted = []
        for idx, item in enumerate(results, 1):
            formatted.append(
                f"{idx}. [{item['category'].upper()}] **{item['key']}** (Relevance: {item.get('score', 'N/A')})\n"
                f"   Content: {item['content']}"
            )
        return f"Memories retrieved for '{query}':\n\n" + "\n\n".join(formatted)


class ManageUserPreferenceTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_user_preference"

    @property
    def description(self) -> str:
        return "Gets or sets user preferences (e.g., preferred name, tone, dev stack, wake word)."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get", "set", "list_all"],
                            "description": "Action to perform: 'get', 'set', or 'list_all'."
                        },
                        "key": {
                            "type": "string",
                            "description": "The preference key (e.g. 'preferred_name', 'theme', 'main_language')."
                        },
                        "value": {
                            "type": "string",
                            "description": "The value to set (required when action is 'set')."
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "list_all").strip().lower()
        if action not in ("get", "set", "list_all"):
            action = "list_all"
        key = str(args.get("key", "")).strip().lower()
        value = str(args.get("value", "")).strip()
        if action == "set" and not key:
            raise ValueError("Parameter 'key' is required for action 'set'.")
        if action == "set" and not value:
            raise ValueError("Parameter 'value' is required for action 'set'.")
        if action == "get" and not key:
            raise ValueError("Parameter 'key' is required for action 'get'.")
        return {"action": action, "key": key, "value": value}

    def execute(self, args: Dict[str, Any]) -> Any:
        action = args["action"]
        key = args["key"]
        value = args["value"]
        
        if action == "set":
            res = memory_service.set_preference(key=key, value=value)
            return f"Preference set: '{res['key']}' = '{res['value']}'"
        elif action == "get":
            val = memory_service.get_preference(key=key)
            if val is not None:
                return f"Preference '{key}': {val}"
            return f"Preference '{key}' is not set."
        else:
            all_prefs = memory_service.get_all_preferences()
            if not all_prefs:
                return "No user preferences currently set."
            return "Current User Preferences:\n" + "\n".join([f"- **{k}**: {v}" for k, v in all_prefs.items()])


class ManageTasksTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_tasks"

    @property
    def description(self) -> str:
        return "Creates, lists, or updates user tasks and to-do items."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "list", "complete", "update_status"],
                            "description": "Action to perform: 'add', 'list', 'complete', or 'update_status'."
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the task (required when action is 'add')."
                        },
                        "project": {
                            "type": "string",
                            "description": "Project name associated with the task."
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Priority level of the task."
                        },
                        "task_id": {
                            "type": "integer",
                            "description": "Task ID (required when action is 'complete' or 'update_status')."
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "Status to filter by or set."
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "list").strip().lower()
        if action not in ("add", "list", "complete", "update_status"):
            action = "list"
        title = str(args.get("title", "")).strip()
        project = str(args.get("project", "General")).strip()
        priority = str(args.get("priority", "medium")).strip().lower()
        task_id = args.get("task_id")
        status = str(args.get("status", "pending")).strip().lower()
        
        if action == "add" and not title:
            raise ValueError("Parameter 'title' is required for action 'add'.")
        if action in ("complete", "update_status") and not task_id:
            raise ValueError(f"Parameter 'task_id' is required for action '{action}'.")
            
        return {
            "action": action,
            "title": title,
            "project": project,
            "priority": priority,
            "task_id": int(task_id) if task_id else None,
            "status": status
        }

    def execute(self, args: Dict[str, Any]) -> Any:
        action = args["action"]
        if action == "add":
            task = memory_service.add_task(
                title=args["title"],
                project=args["project"],
                priority=args["priority"]
            )
            return f"Task created successfully [ID: {task['id']}]: '{task['title']}' (Project: {task['project']}, Priority: {task['priority']})"
            
        elif action == "complete":
            task = memory_service.update_task_status(task_id=args["task_id"], status="completed")
            if task:
                return f"Task ID {args['task_id']} marked as completed: '{task['title']}'"
            return f"Task ID {args['task_id']} not found."
            
        elif action == "update_status":
            task = memory_service.update_task_status(task_id=args["task_id"], status=args["status"])
            if task:
                return f"Task ID {args['task_id']} status updated to '{args['status']}': '{task['title']}'"
            return f"Task ID {args['task_id']} not found."
            
        else:  # list
            tasks = memory_service.list_tasks(status=args.get("status"))
            if not tasks:
                return "No tasks found matching criteria."
            lines = [
                f"- [ID: {t['id']}] **{t['title']}** (Status: {t['status']}, Priority: {t['priority']}, Project: {t['project']})"
                for t in tasks
            ]
            return "Current Task List:\n" + "\n".join(lines)


class GetConversationHistoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_conversation_history"

    @property
    def description(self) -> str:
        return "Retrieves past conversation turns to recall context from earlier chat sessions."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent conversation messages to retrieve (default: 10)."
                        }
                    }
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = args.get("limit", 10)
        try:
            limit = int(limit)
        except Exception:
            limit = 10
        return {"limit": min(max(limit, 1), 50)}

    def execute(self, args: Dict[str, Any]) -> Any:
        limit = args["limit"]
        history = memory_service.get_conversation_history(limit=limit)
        if not history:
            return "No previous conversation history found."
        lines = [f"{msg['role'].capitalize()}: {msg['content']}" for msg in history]
        return "Recent Conversation History:\n\n" + "\n".join(lines)
