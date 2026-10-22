"""
Web Research Tools
Provides web search (DuckDuckGo with modular Tavily support) and webpage text extractor.
"""
from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional
import warnings

import requests
from bs4 import BeautifulSoup

from .base import BaseTool

# Suppress harmless package rename warnings from duckduckgo_search
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")


# =====================================================================
# 1. Modular Search Providers
# =====================================================================

class BaseSearchProvider(ABC):
    """Abstract interface for web search backends."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Execute search and return a list of dicts with 'title', 'href', 'body'.
        """
        pass


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo search provider. Completely free, no API key required."""

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                raise ImportError(
                    "Package 'duckduckgo-search' is required. Install via: pip install duckduckgo-search"
                )

            with DDGS(timeout=10) as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", "No Title"),
                "href": item.get("href", ""),
                "body": item.get("body", ""),
            })
        return results


class TavilySearchProvider(BaseSearchProvider):
    """Tavily search provider for high-accuracy AI search (optional)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.api_key:
            raise ValueError("Tavily API key is not configured in .env (TAVILY_API_KEY).")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "href": item.get("url", ""),
                "body": item.get("content", ""),
            })
        return results


# =====================================================================
# 2. Agent Web Tools
# =====================================================================

class WebSearchTool(BaseTool):
    """Tool to search the internet for answers, news, and research."""

    name = "web_search"
    description = (
        "Searches the web for up-to-date information, news, facts, and documentation. "
        "Returns a list of relevant search results with titles, URLs, and summaries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query keywords or question.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 10).",
            },
        },
        "required": ["query"],
    }
    requires_confirmation = False

    def __init__(self, provider: Optional[BaseSearchProvider] = None):
        self.provider = provider or DuckDuckGoSearchProvider()

    def execute(self, query: str, max_results: int = 5, **kwargs: Any) -> str:
        clean_query = query.strip()
        if not clean_query:
            return "Error: Search query cannot be empty."

        limit = max(1, min(int(max_results), 10))

        try:
            results = self.provider.search(clean_query, max_results=limit)
            if not results:
                return f"No search results found for query: '{clean_query}'."

            lines = [f"Web search results for: '{clean_query}' ({len(results)} found)\n"]
            for i, item in enumerate(results, start=1):
                title = item.get("title", "No Title")
                href = item.get("href", "")
                snippet = item.get("body", "No snippet available.")
                lines.append(f"{i}. {title}")
                lines.append(f"   URL: {href}")
                lines.append(f"   Summary: {snippet}\n")

            return "\n".join(lines)
        except Exception as e:
            return f"Error executing web search: {type(e).__name__}: {str(e)}"


class FetchWebpageTool(BaseTool):
    """Tool to fetch and read clean text content from a web page."""

    name = "fetch_webpage"
    description = (
        "Fetches and extracts clean, human-readable text from a public web page URL. "
        "Useful for in-depth research after finding a URL from web_search."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full HTTP/HTTPS URL of the web page to read.",
            },
        },
        "required": ["url"],
    }
    requires_confirmation = False

    def execute(self, url: str, **kwargs: Any) -> str:
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            return f"Error: Invalid URL '{url}'. URL must begin with http:// or https://."

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            response = requests.get(target_url, headers=headers, timeout=12)
            response.raise_for_status()

            # Parse HTML and remove non-content elements
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside"]):
                tag.decompose()

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Page"

            # Extract clean body text
            text = soup.get_text(separator="\n", strip=True)

            # Collapse excess blank lines
            cleaned_text = re.sub(r"\n{3,}", "\n\n", text).strip()

            if not cleaned_text:
                return f"Fetched '{target_url}', but no readable text content was found."

            # Guard against huge pages overwhelming LLM context
            max_chars = 6000
            if len(cleaned_text) > max_chars:
                cleaned_text = (
                    cleaned_text[:max_chars]
                    + f"\n\n[... Content truncated: showing first {max_chars} characters ...]"
                )

            return f"Page Title: {title}\nURL: {target_url}\n\nContent:\n{cleaned_text}"

        except requests.exceptions.Timeout:
            return f"Error: Request timed out while attempting to load '{target_url}' (12s limit)."
        except requests.exceptions.HTTPError as he:
            return f"HTTP Error fetching '{target_url}': Status {he.response.status_code}."
        except Exception as e:
            return f"Error fetching webpage '{target_url}': {type(e).__name__}: {str(e)}"
