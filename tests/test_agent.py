import sys
import os

# Append workspace root to path to ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.registry import registry
from backend.ai.tools import OpenBrowserTool, SearchWebTool

def test_registry():
    print("\n--- Testing Registry Registration ---")
    assert registry.get_tool("open_browser") is not None
    assert registry.get_tool("search_web") is not None
    print("[PASS] Tools correctly registered in the central tool registry.")

def test_open_browser_validation():
    print("\n--- Testing open_browser validation ---")
    tool = registry.get_tool("open_browser")
    
    # 1. Test missing argument
    try:
        tool.validate_args({})
        assert False, "Should have failed on missing argument"
    except Exception as e:
        print("Missing arg handled (Expected error):", e)
        
    # 2. Test invalid browser
    try:
        tool.validate_args({"browser_name": "malicious_browser"})
        assert False, "Should have failed on invalid browser name"
    except ValueError as ve:
        print("Invalid browser handled (Expected error):", ve)
        assert "safe approved list" in str(ve)
        
    # 3. Test valid browser
    validated = tool.validate_args({"browser_name": "chrome"})
    print("Validated args:", validated)
    assert validated["browser_name"] == "chrome"
    
    print("[PASS] open_browser validation is correct.")

def test_search_web_validation():
    print("\n--- Testing search_web validation ---")
    tool = registry.get_tool("search_web")
    
    # 1. Test missing query
    try:
        tool.validate_args({})
        assert False, "Should have failed on missing query"
    except Exception as e:
        print("Missing query handled (Expected error):", e)
        
    # 2. Test query length limit
    try:
        tool.validate_args({"query": "a" * 201})
        assert False, "Should have failed on query length limit"
    except ValueError as ve:
        print("Query length handled (Expected error):", ve)
        assert "exceeds maximum limit" in str(ve)
        
    # 3. Test dangerous command separators
    try:
        tool.validate_args({"query": "python; rm -rf /"})
        assert False, "Should have failed on dangerous characters"
    except ValueError as ve:
        print("Dangerous characters handled (Expected error):", ve)
        assert "Dangerous character tokens detected" in str(ve)
        
    # 4. Test valid search execution
    validated = tool.validate_args({"query": "FastAPI tutorials", "browser": "chrome"})
    print("Validated search args:", validated)
    assert validated["query"] == "FastAPI tutorials"
    assert validated["browser"] == "chrome"
    
    # Run mock/headless execution (it calls Popen/webbrowser in background, we won't block)
    res = tool.execute(validated)
    print("Execution result:", res)
    assert "Successfully executed web search" in res
    
    print("[PASS] search_web validation is correct.")

if __name__ == "__main__":
    print("Starting JARVIS V3 Agent & Tools Validation tests...")
    try:
        test_registry()
        test_open_browser_validation()
        test_search_web_validation()
        print("\nAll Agent & Registry Validation tests passed successfully!")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n[FAIL] Test assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error during tests: {e}")
        sys.exit(1)
