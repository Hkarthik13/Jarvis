import asyncio
from typing import Any, Dict, List
from backend.ai.registry import BaseTool, registry
from backend.knowledge.engine import knowledge_engine
from backend.utils.logger import logger

class QueryPersonalKnowledgeTool(BaseTool):
    @property
    def name(self) -> str:
        return "query_personal_knowledge"

    @property
    def description(self) -> str:
        return (
            "Searches personal documents (Resume, Projects, PDFs, Notes, Documentation) "
            "using semantic RAG vector retrieval to answer specific questions. "
            "Use whenever the user asks about their projects (e.g. 'what technologies did I use in AI Resume Analyzer?'), "
            "their resume, personal technical notes, or documentation."
        )

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
                            "description": "The question to search for in personal documents."
                        },
                        "category": {
                            "type": "string",
                            "description": "Optional category filter: 'resume', 'project', 'notes', 'pdf', 'documentation', or 'all'."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query") or args.get("question") or args.get("q") or ""
        if not query.strip():
            raise ValueError("Parameter 'query' cannot be empty.")
        category = args.get("category", "all")
        return {"query": query.strip(), "category": category}

    def execute(self, args: Dict[str, Any]) -> Any:
        query = args["query"]
        category = args.get("category")
        citations = knowledge_engine.search_chunks(query, category=category, top_k=4)
        if not citations:
            return f"No matching document excerpts found in your personal knowledge vault for query: '{query}'."

        parts = [f"Found {len(citations)} relevant document excerpts from personal knowledge vault:"]
        for idx, c in enumerate(citations):
            parts.append(f"\n[{idx+1}] Source: **{c.title}** ({c.filename} | Category: {c.category} | Relevance: {c.relevance_score})\nExcerpt:\n{c.excerpt}")
        return "\n".join(parts)


class IndexDocumentTool(BaseTool):
    @property
    def name(self) -> str:
        return "index_personal_document"

    @property
    def description(self) -> str:
        return (
            "Indexes a document file path or text content into the personal knowledge vault for RAG search. "
            "Supported formats: .md, .txt, .pdf, .py, .json."
        )

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
                        "file_path": {
                            "type": "string",
                            "description": "Path to document file on laptop."
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional title for document."
                        },
                        "content": {
                            "type": "string",
                            "description": "Raw text content to index directly."
                        },
                        "category": {
                            "type": "string",
                            "description": "Category: 'resume', 'project', 'notes', 'pdf', 'documentation'."
                        }
                    }
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = args.get("file_path")
        content = args.get("content")
        if not file_path and not content:
            raise ValueError("Either 'file_path' or 'content' must be provided.")
        category = args.get("category", "notes")
        title = args.get("title", "Indexed Note")
        return {"file_path": file_path, "content": content, "category": category, "title": title}

    def execute(self, args: Dict[str, Any]) -> Any:
        if args.get("file_path"):
            res = knowledge_engine.index_file(args["file_path"], category=args["category"], title=args.get("title"))
            return f"Successfully indexed file '{res['filename']}' ({res['total_chunks']} chunks) in category '{res['category']}'."
        else:
            res = knowledge_engine.index_text(title=args["title"], content=args["content"], category=args["category"])
            return f"Successfully indexed note '{res['title']}' ({res['total_chunks']} chunks)."


class ListPersonalDocumentsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_personal_documents"

    @property
    def description(self) -> str:
        return "Lists all indexed documents and files in the user's personal knowledge vault."

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
                        "category": {
                            "type": "string",
                            "description": "Optional category filter: 'all', 'resume', 'project', 'notes', 'pdf', 'documentation'"
                        }
                    }
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"category": args.get("category", "all")}

    def execute(self, args: Dict[str, Any]) -> Any:
        docs = knowledge_engine.list_documents(category=args.get("category"))
        if not docs:
            return "Your personal knowledge vault currently has no indexed documents."
        
        output = [f"Found {len(docs)} indexed documents in knowledge vault:"]
        for d in docs:
            output.append(f"- 📄 **{d['title']}** (`{d['filename']}`) [{d['category'].upper()}] - {d['total_chunks']} chunks ({round(d['file_size']/1024, 1)} KB)")
        return "\n".join(output)


# Register knowledge tools into global registry
registry.register(QueryPersonalKnowledgeTool())
registry.register(IndexDocumentTool())
registry.register(ListPersonalDocumentsTool())
