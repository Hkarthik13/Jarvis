import httpx
from bs4 import BeautifulSoup
import urllib.parse

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def run():
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote("FastAPI python tutorial")
    res = httpx.post("https://html.duckduckgo.com/html/", data={"q": "FastAPI python tutorial"}, headers=headers, follow_redirects=True)
    print("Status:", res.status_code)

    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for result in soup.find_all("div", class_="result"):
        title_tag = result.find("a", class_="result__snippet")
        link_tag = result.find("a", class_="result__url")
        title_header = result.find("a", class_="result__a")
        if title_header and link_tag:
            title = title_header.get_text().strip()
            link = link_tag.get("href", "").strip()
            snippet = title_tag.get_text().strip() if title_tag else ""
            results.append((title, link, snippet))

    print("Found results:", len(results))
    for t, l, s in results[:3]:
        print(f"- {t} -> {l}\n  {s}")

if __name__ == "__main__":
    run()
