from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        results = list(ddgs.text("python tutorial", max_results=3))
        print("DDG Results count:", len(results))
        for r in results:
            print("Title:", r.get("title"))
            print("Href:", r.get("href"))
except Exception as e:
    print("DDG Exception:", e)
