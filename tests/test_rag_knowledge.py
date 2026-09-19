import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.knowledge.engine import knowledge_engine
from backend.knowledge.parser import chunk_text, extract_text_from_file
from backend.ai.registry import registry
from backend.config import settings

class TestVersion9RAGKnowledge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.headers = {"X-Jarvis-API-Key": settings.jarvis_api_key or "jarvis_secure_key_123"}
        # Scan vault with force=True to ensure up-to-date embeddings and chunks
        knowledge_engine.scan_vault(force=True)

    def test_01_parser_and_chunking(self):
        """Test text chunker with sliding window overlap."""
        sample_text = (
            "# Project Overview\n\n"
            "AI Resume Analyzer is a modern tool built with FastAPI and React.\n\n"
            "## Architecture\n\n"
            "It uses Groq LLM for evaluation, FAISS for vector search, and Docker for deployment.\n\n"
            "## Requirements\n\n"
            "Requires Python 3.11, PostgreSQL, Redis, and PyPDF2."
        )
        chunks = chunk_text(sample_text, chunk_size=120, overlap=30, min_chunk_size=30)
        self.assertGreaterEqual(len(chunks), 2)
        for c in chunks:
            self.assertTrue(len(c["content"]) > 0)

    def test_02_vault_documents_indexed(self):
        """Verify that vault documents like AI Resume Analyzer and Resume are indexed."""
        docs = knowledge_engine.list_documents()
        self.assertGreaterEqual(len(docs), 2)
        filenames = [d["filename"] for d in docs]
        self.assertTrue(any("ai_resume_analyzer" in f for f in filenames))
        self.assertTrue(any("resume" in f for f in filenames))

    def test_03_hybrid_semantic_search(self):
        """Test hybrid vector search for specific project technologies."""
        # Query about AI Resume Analyzer technologies
        query = "What technologies are used in the AI Resume Analyzer project?"
        citations = knowledge_engine.search_chunks(query, top_k=3)
        self.assertGreater(len(citations), 0)
        
        top_cite = citations[0]
        self.assertTrue("ai_resume_analyzer" in top_cite.filename.lower() or "resume" in top_cite.filename.lower())
        self.assertGreater(top_cite.relevance_score, 0.2)
        has_fastapi = any("fastapi" in c.excerpt.lower() for c in citations)
        self.assertTrue(has_fastapi)

    def test_04_rag_query_synthesis(self):
        """Test end-to-end RAG query answering."""
        query = "AI Resume Analyzer project-la what technologies were used?"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resp = loop.run_until_complete(knowledge_engine.query_rag(query, top_k=3))
        loop.close()

        self.assertEqual(resp.query, query)
        self.assertGreater(len(resp.citations), 0)
        self.assertTrue(len(resp.answer) > 20)
        # Check that relevant technologies are mentioned in the answer
        answer_lower = resp.answer.lower()
        self.assertTrue(
            "fastapi" in answer_lower or "groq" in answer_lower or "react" in answer_lower or "faiss" in answer_lower
        )

    def test_05_ai_tools_registered(self):
        """Verify that RAG AI tools are registered and executable."""
        tool_names = list(registry._tools.keys())
        self.assertIn("query_personal_knowledge", tool_names)
        self.assertIn("index_personal_document", tool_names)
        self.assertIn("list_personal_documents", tool_names)

        # Execute list tool
        list_tool = registry.get_tool("list_personal_documents")
        res_list = list_tool.execute({"category": "all"})
        self.assertIn("ai resume analyzer", res_list.lower())

        # Execute query tool
        query_tool = registry.get_tool("query_personal_knowledge")
        res_query = query_tool.execute({"query": "AI Resume Analyzer technologies"})
        self.assertTrue(len(res_query) > 30)

    def test_06_rest_api_knowledge_endpoints(self):
        """Test knowledge REST endpoints."""
        # 1. GET /api/knowledge/documents
        resp_docs = self.client.get("/api/knowledge/documents", headers=self.headers)
        self.assertEqual(resp_docs.status_code, 200)
        docs_data = resp_docs.json()["documents"]
        self.assertGreaterEqual(len(docs_data), 2)

        # 2. POST /api/knowledge/query
        payload = {
            "query": "What technologies are used in AI Resume Analyzer?",
            "top_k": 3
        }
        resp_query = self.client.post("/api/knowledge/query", json=payload, headers=self.headers)
        self.assertEqual(resp_query.status_code, 200)
        qdata = resp_query.json()
        self.assertGreater(len(qdata["citations"]), 0)
        self.assertTrue(len(qdata["answer"]) > 20)

        # 3. POST /api/knowledge/index-file with direct content
        note_payload = {
            "title": "Flutter Architecture Notes",
            "content": "Flutter uses Provider, BLoC, and Riverpod for state management. Glassmorphism styling uses BackdropFilter and custom gradients.",
            "category": "notes"
        }
        resp_index = self.client.post("/api/knowledge/index-file", json=note_payload, headers=self.headers)
        self.assertEqual(resp_index.status_code, 200)
        indexed_doc = resp_index.json()["document"]
        self.assertEqual(indexed_doc["title"], "Flutter Architecture Notes")

        # 4. Search newly indexed note
        resp_note_query = self.client.post(
            "/api/knowledge/query",
            json={"query": "How is glassmorphism done in Flutter?"},
            headers=self.headers
        )
        self.assertEqual(resp_note_query.status_code, 200)
        self.assertTrue(any("Flutter Architecture Notes" in c["title"] for c in resp_note_query.json()["citations"]))


if __name__ == "__main__":
    unittest.main()
