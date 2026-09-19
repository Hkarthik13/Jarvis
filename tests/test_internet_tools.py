import sys
import os

# Append workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.registry import registry
import backend.ai.tools  # Registers all tools

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

def test_live_weather():
    safe_print("\n--- 1. Testing Live Weather Tool ---")
    tool = registry.get_tool("get_live_weather")
    assert tool is not None, "get_live_weather is not registered in registry"
    
    # Test valid city
    res = tool.execute({"location": "Chennai"})
    safe_print("Weather Output:\n", res)
    assert "Live Weather for Chennai" in res
    assert "Temperature:" in res
    safe_print("[PASS] Live Weather retrieved successfully.")

def test_web_search_live():
    safe_print("\n--- 2. Testing Live Web Search Tool ---")
    tool = registry.get_tool("search_web_live")
    assert tool is not None, "search_web_live is not registered in registry"
    
    res = tool.execute({"query": "FastAPI Python tutorial", "category": "general"})
    safe_print("Web Search Output:\n", res)
    assert "Live search results" in res
    assert "Link:" in res
    safe_print("[PASS] Live Web Search executed successfully.")

def test_youtube_search():
    safe_print("\n--- 3. Testing YouTube Search Tool ---")
    tool = registry.get_tool("search_youtube")
    assert tool is not None, "search_youtube is not registered in registry"
    
    res = tool.execute({"query": "Python FastAPI tutorials"})
    safe_print("YouTube Search Output:\n", res)
    assert "YouTube" in res
    assert "Link:" in res
    safe_print("[PASS] YouTube Search executed successfully.")

def test_webpage_content():
    safe_print("\n--- 4. Testing Webpage Content Reader Tool ---")
    tool = registry.get_tool("fetch_webpage_content")
    assert tool is not None, "fetch_webpage_content is not registered in registry"
    
    res = tool.execute({"url": "https://fastapi.tiangolo.com"})
    safe_print("Webpage Content Output:\n", res[:400] + "...")
    assert "Page Title:" in res
    assert "Content:" in res
    safe_print("[PASS] Webpage content parsed and read successfully.")

if __name__ == "__main__":
    safe_print("=== Starting JARVIS Version 4 Internet Tools Validation ===")
    try:
        test_live_weather()
        test_web_search_live()
        test_youtube_search()
        test_webpage_content()
        safe_print("\n[ALL PASS] All Version 4 Internet Tools validated successfully!")
        sys.exit(0)
    except AssertionError as ae:
        safe_print(f"\n[FAIL] Test assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n[FAIL] Unexpected error during tests: {e}")
        sys.exit(1)
