import re
import urllib.parse
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup

from backend.ai.registry import BaseTool, registry
from backend.utils.logger import logger

# Standard browser headers to ensure search engines return clean HTML
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# WMO Weather interpretation codes
WEATHER_CODES = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy ⛅",
    3: "Overcast ☁️",
    45: "Fog 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Light drizzle 🌦️",
    53: "Moderate drizzle 🌦️",
    55: "Dense drizzle 🌧️",
    61: "Slight rain 🌧️",
    63: "Moderate rain 🌧️",
    65: "Heavy rain 🌧️",
    71: "Slight snow fall 🌨️",
    73: "Moderate snow fall 🌨️",
    75: "Heavy snow fall ❄️",
    80: "Slight rain showers 🌦️",
    81: "Moderate rain showers 🌧️",
    82: "Violent rain showers ⛈️",
    95: "Thunderstorm ⛈️",
    96: "Thunderstorm with slight hail ⛈️",
    99: "Thunderstorm with heavy hail ⛈️",
}


class GetLiveWeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_live_weather"

    @property
    def description(self) -> str:
        return "Fetches real-time live weather, temperature, humidity, and forecast for any city or location."

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
                        "location": {
                            "type": "string",
                            "description": "City or location name (e.g., 'Chennai', 'London', 'New York', 'Tokyo')."
                        }
                    },
                    "required": ["location"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        loc = args.get("location")
        if not loc or not str(loc).strip():
            raise ValueError("Parameter 'location' is required.")
        return {"location": str(loc).strip()}

    def execute(self, args: Dict[str, Any]) -> Any:
        location = args["location"]
        logger.info(f"Fetching live weather for location: '{location}'")
        try:
            with httpx.Client(timeout=10.0, headers=HEADERS) as client:
                # 1. Geocoding lookup
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
                geo_res = client.get(geo_url)
                geo_data = geo_res.json()
                
                if not geo_data.get("results"):
                    return f"Could not find coordinates for location '{location}'. Please verify the city name."
                    
                city_info = geo_data["results"][0]
                lat = city_info["latitude"]
                lon = city_info["longitude"]
                city_name = city_info.get("name", location)
                country = city_info.get("country", "")
                
                # 2. Weather lookup
                weather_url = (
                    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                    f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
                )
                w_res = client.get(weather_url)
                w_data = w_res.json()
                current = w_data.get("current", {})
                
                temp = current.get("temperature_2m")
                feels_like = current.get("apparent_temperature")
                humidity = current.get("relative_humidity_2m")
                wind = current.get("wind_speed_10m")
                code = current.get("weather_code", 0)
                condition = WEATHER_CODES.get(code, "Clear")
                
                result = (
                    f"Live Weather for {city_name}, {country}:\n"
                    f"- Condition: {condition}\n"
                    f"- Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
                    f"- Humidity: {humidity}%\n"
                    f"- Wind Speed: {wind} km/h"
                )
                return result
        except Exception as e:
            logger.error(f"Failed to fetch live weather for '{location}': {e}")
            return f"Error retrieving weather data for '{location}': {str(e)}"


def extract_clean_url(href: str, fallback_text: str = "") -> str:
    """Extracts genuine destination URL from DuckDuckGo redirect link or fallback."""
    if href and "uddg=" in href:
        try:
            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params and params["uddg"]:
                return params["uddg"][0]
        except Exception:
            pass
    if href and (href.startswith("http://") or href.startswith("https://")):
        return href
    if fallback_text:
        clean = fallback_text.strip()
        if not clean.startswith("http"):
            clean = "https://" + clean
        return clean
    return href or ""


def fetch_ddg_results(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Helper to query DuckDuckGo Lite and extract clean title, url, snippet."""
    results = []
    try:
        with httpx.Client(timeout=12.0, headers=HEADERS, follow_redirects=True) as client:
            # 1. Primary: DDG Lite
            res = client.post("https://lite.duckduckgo.com/lite/", data={"q": query})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                links = soup.find_all("a", class_="result-link")
                snippets = soup.find_all("td", class_="result-snippet")
                
                for link_tag, snip_tag in zip(links, snippets):
                    title = link_tag.get_text().strip()
                    href = link_tag.get("href", "").strip()
                    clean_url = extract_clean_url(href)
                    snippet = snip_tag.get_text().strip()
                    
                    if any(x in clean_url for x in ("duckduckgo.com/y.js", "bing.com/aclick", "duckduckgo-help-pages", "help.duckduckgo.com")):
                        continue
                    if title.lower() in ("more info", "feedback", "ad", "sponsored"):
                        continue
                        
                    results.append({"title": title, "link": clean_url, "snippet": snippet})
                    if len(results) >= max_results:
                        break
                        
        # 2. Fallback: DDG HTML if Lite had no results
        if not results:
            with httpx.Client(timeout=12.0, headers=HEADERS, follow_redirects=True) as client:
                res = client.post("https://html.duckduckgo.com/html/", data={"q": query})
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    for result in soup.find_all("div", class_="result"):
                        classes = result.get("class", [])
                        if "result--ad" in classes:
                            continue
                        title_header = result.find("a", class_="result__a")
                        link_tag = result.find("a", class_="result__url")
                        snippet_tag = result.find("a", class_="result__snippet")
                        if title_header:
                            raw_href = title_header.get("href", "").strip()
                            title = title_header.get_text().strip()
                            fallback_url = link_tag.get_text().strip() if link_tag else ""
                            link = extract_clean_url(raw_href, fallback_url)
                            snippet = snippet_tag.get_text().strip() if snippet_tag else ""
                            
                            if any(x in link for x in ("duckduckgo.com/y.js", "bing.com/aclick", "duckduckgo-help-pages", "help.duckduckgo.com")):
                                continue
                            if title.lower() in ("more info", "feedback", "ad", "sponsored"):
                                continue
                                
                            results.append({"title": title, "link": link, "snippet": snippet})
                            if len(results) >= max_results:
                                break
    except Exception as e:
        logger.error(f"Error fetching DDG search results for '{query}': {e}")
        
    return results


class SearchWebLiveTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_web_live"

    @property
    def description(self) -> str:
        return "Performs live web search on DuckDuckGo and returns real-time summaries, facts, and links."

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
                            "description": "The search term or question to search the live web for."
                        },
                        "category": {
                            "type": "string",
                            "enum": ["general", "news"],
                            "description": "Whether to search general web results or latest news."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        q = args.get("query")
        if not q or not str(q).strip():
            raise ValueError("Parameter 'query' is required.")
        cat = args.get("category", "general").lower().strip()
        if cat not in ("general", "news"):
            cat = "general"
        return {"query": str(q).strip(), "category": cat}

    def execute(self, args: Dict[str, Any]) -> Any:
        query = args["query"]
        category = args["category"]
        logger.info(f"Executing live web search: '{query}' (category: {category})")
        try:
            search_query = f"{query} news" if category == "news" else query
            raw_results = fetch_ddg_results(search_query, max_results=4)
            
            if not raw_results:
                return f"No search results found on the live web for '{query}'."
                
            results_text = [
                f"{idx}. **{r['title']}**\n   {r['snippet']}\n   Link: {r['link']}"
                for idx, r in enumerate(raw_results, 1)
            ]
            return f"Live search results for '{query}':\n\n" + "\n\n".join(results_text)
        except Exception as e:
            logger.error(f"Live search failed for '{query}': {e}")
            return f"Error executing live web search: {str(e)}"


class SearchYouTubeTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_youtube"

    @property
    def description(self) -> str:
        return "Searches YouTube for videos, tutorials, reviews, or music and returns video titles and links."

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
                            "description": "The search query for YouTube videos."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        q = args.get("query")
        if not q or not str(q).strip():
            raise ValueError("Parameter 'query' is required.")
        return {"query": str(q).strip()}

    def execute(self, args: Dict[str, Any]) -> Any:
        query = args["query"]
        logger.info(f"Searching YouTube for: '{query}'")
        try:
            raw_results = fetch_ddg_results(f"site:youtube.com {query}", max_results=3)
            
            if not raw_results:
                yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                return f"YouTube Search Link for '{query}': {yt_url}"
                
            results_text = [
                f"{idx}. **{r['title']}**\n   {r['snippet']}\n   Link: {r['link']}"
                for idx, r in enumerate(raw_results, 1)
            ]
            return f"YouTube video results for '{query}':\n\n" + "\n\n".join(results_text)
        except Exception as e:
            logger.error(f"YouTube search error for '{query}': {e}")
            yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            return f"YouTube Search Link for '{query}': {yt_url}"


class FetchWebpageContentTool(BaseTool):
    @property
    def name(self) -> str:
        return "fetch_webpage_content"

    @property
    def description(self) -> str:
        return "Fetches and reads text content from a web URL (e.g. documentation, article, blog post)."

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
                        "url": {
                            "type": "string",
                            "description": "The HTTP/HTTPS URL of the webpage to read."
                        }
                    },
                    "required": ["url"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url")
        if not url or not str(url).strip():
            raise ValueError("Parameter 'url' is required.")
        cleaned = str(url).strip()
        if not cleaned.startswith(("http://", "https://")):
            cleaned = "https://" + cleaned
        return {"url": cleaned}

    def execute(self, args: Dict[str, Any]) -> Any:
        url = args["url"]
        logger.info(f"Fetching webpage content from: {url}")
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=HEADERS) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return f"Failed to retrieve page content (HTTP status: {response.status_code})."
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove unwanted non-content elements
                for tag in soup(["script", "style", "nav", "footer", "aside", "header", "noscript", "svg"]):
                    tag.decompose()
                    
                # Extract page title
                title = soup.title.string.strip() if soup.title and soup.title.string else "Web Page"
                
                # Extract clean paragraph text
                paragraphs = [p.get_text().strip() for p in soup.find_all(["p", "h1", "h2", "h3", "li", "code"]) if p.get_text().strip()]
                full_text = "\n".join(paragraphs)
                
                # Cap at 1500 chars to avoid prompt token explosion
                if len(full_text) > 1500:
                    full_text = full_text[:1500] + "...\n[Content truncated for length]"
                    
                return f"Page Title: {title}\nURL: {url}\n\nContent:\n{full_text}"
        except Exception as e:
            logger.error(f"Error fetching webpage content from '{url}': {e}")
            return f"Error reading webpage content from '{url}': {str(e)}"
