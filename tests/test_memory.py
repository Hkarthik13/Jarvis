import sys
import os

# Append workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.memory.service import memory_service
from backend.ai.registry import registry
import backend.ai.tools  # Ensures all BaseTools are registered

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                new_args.append(arg.encode('ascii', errors='replace').decode('ascii'))
            else:
                new_args.append(arg)
        print(*new_args, **kwargs)

def test_save_and_recall_memory():
    safe_print("\n--- 1. Testing Memory Persistence & Semantic Recall ---")
    
    # Store project memory as given in user example
    entry = memory_service.save_memory(
        content="My main project is Digital Behaviour Twin, an AI simulation system.",
        key="main_project",
        category="project",
        tags=["ai", "twin", "simulation", "primary"]
    )
    safe_print(f"Saved memory: {entry['key']} -> {entry['content']}")
    assert entry["id"] is not None
    assert entry["key"] == "main_project"
    
    # Store second fact
    memory_service.save_memory(
        content="I prefer dark mode UI and Python FastAPI backend.",
        key="dev_preference",
        category="preference",
        tags=["ui", "fastapi", "python"]
    )
    
    # Recall 1: Querying main project
    results = memory_service.recall_memories("What is my main project?", top_k=3)
    safe_print("Recall results for 'What is my main project?':")
    for r in results:
        safe_print(f"  - [{r['category']}] {r['key']}: {r['content']} (Score: {r['score']})")
        
    assert len(results) > 0
    assert "Digital Behaviour Twin" in results[0]["content"]
    assert results[0]["key"] == "main_project"
    safe_print("[PASS] Semantic Recall returned exact matching project memory as #1 result.")

    # Recall 2: Querying dev preferences
    results_pref = memory_service.recall_memories("What tech stack and theme do I like?", top_k=2)
    assert len(results_pref) > 0
    assert "FastAPI" in results_pref[0]["content"] or "dark mode" in results_pref[0]["content"]
    safe_print("[PASS] Semantic Recall correctly retrieved preference memory.")

def test_user_preferences():
    safe_print("\n--- 2. Testing User Preference Key-Value Store ---")
    
    pref = memory_service.set_preference("preferred_name", "Alex", category="identity")
    safe_print(f"Set preference: {pref['key']} = {pref['value']}")
    
    val = memory_service.get_preference("preferred_name")
    assert val == "Alex"
    
    all_prefs = memory_service.get_all_preferences()
    assert "preferred_name" in all_prefs
    safe_print(f"All preferences: {all_prefs}")
    safe_print("[PASS] User preferences set and retrieved successfully.")

def test_task_management():
    safe_print("\n--- 3. Testing Task and To-Do Management ---")
    
    # Add task
    task = memory_service.add_task(
        title="Implement SQLite vector embeddings for JARVIS memory",
        description="Add dense vector cosine similarity and full-text ranking",
        project="Jarvis V5",
        priority="high"
    )
    safe_print(f"Added task: [{task['id']}] {task['title']} ({task['project']})")
    assert task["id"] is not None
    assert task["status"] == "pending"
    
    # List tasks
    pending = memory_service.list_tasks(status="pending")
    assert any(t["id"] == task["id"] for t in pending)
    
    # Complete task
    updated = memory_service.update_task_status(task["id"], "completed")
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None
    safe_print(f"Completed task: [{updated['id']}] Status: {updated['status']}")
    safe_print("[PASS] Task management lifecycle passed.")

def test_conversation_history():
    safe_print("\n--- 4. Testing Conversation History Persistence ---")
    import uuid
    sess_id = f"test_session_{uuid.uuid4().hex[:8]}"
    
    memory_service.save_conversation(role="user", content="Jarvis, remember that my main project is Digital Behaviour Twin.", session_id=sess_id)
    memory_service.save_conversation(role="assistant", content="I have remembered that your main project is Digital Behaviour Twin.", session_id=sess_id)
    
    history = memory_service.get_conversation_history(session_id=sess_id, limit=5)
    safe_print(f"Retrieved {len(history)} messages from session '{sess_id}'")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    safe_print("[PASS] Conversation history persisted and retrieved successfully.")


def test_memory_tools_registry():
    safe_print("\n--- 5. Testing BaseTool Memory Implementations in Tool Registry ---")
    
    # Verify tool registration
    assert registry.get_tool("remember_fact") is not None
    assert registry.get_tool("recall_memory") is not None
    assert registry.get_tool("manage_user_preference") is not None
    assert registry.get_tool("manage_tasks") is not None
    assert registry.get_tool("get_conversation_history") is not None
    
    # Execute remember_fact via registry
    res_rem = registry.execute_tool("remember_fact", {
        "content": "Our server deployment uses Docker on port 8000",
        "key": "server_deployment",
        "category": "note"
    })
    safe_print("Tool 'remember_fact' execution result:\n", res_rem)
    assert "Successfully remembered" in res_rem
    
    # Execute recall_memory via registry
    res_rec = registry.execute_tool("recall_memory", {
        "query": "Where is the server deployed and what port?"
    })
    safe_print("Tool 'recall_memory' execution result:\n", res_rec)
    assert "Docker on port 8000" in res_rec
    
    # Execute manage_tasks via registry
    res_task = registry.execute_tool("manage_tasks", {
        "action": "add",
        "title": "Review memory test suite",
        "project": "Jarvis"
    })
    safe_print("Tool 'manage_tasks' add result:\n", res_task)
    assert "Task created successfully" in res_task
    
    # Execute manage_user_preference via registry
    res_pref = registry.execute_tool("manage_user_preference", {
        "action": "set",
        "key": "editor",
        "value": "VS Code"
    })
    safe_print("Tool 'manage_user_preference' result:\n", res_pref)
    assert "Preference set" in res_pref
    
    safe_print("[PASS] All BaseTool memory tools executed successfully via registry.")

if __name__ == "__main__":
    safe_print("=== Starting JARVIS Version 5 Memory System Validation ===")
    try:
        test_save_and_recall_memory()
        test_user_preferences()
        test_task_management()
        test_conversation_history()
        test_memory_tools_registry()
        safe_print("\n[ALL PASS] JARVIS Version 5 Memory System validated successfully!")
        sys.exit(0)
    except AssertionError as ae:
        safe_print(f"\n[FAIL] Assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n[FAIL] Unexpected error: {e}")
        sys.exit(1)
