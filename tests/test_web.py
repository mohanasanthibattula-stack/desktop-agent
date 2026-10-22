"""
Unit tests for Milestone 3: Web Research Tools.
Tests DuckDuckGo search provider, Tavily provider interface, WebSearchTool, and FetchWebpageTool.
"""
from unittest.mock import MagicMock, patch
import pytest

from agent.tools.registry import ToolRegistry
from agent.tools.web import (
    BaseSearchProvider,
    DuckDuckGoSearchProvider,
    FetchWebpageTool,
    TavilySearchProvider,
    WebSearchTool,
)


class MockSearchProvider(BaseSearchProvider):
    """Mock search provider for fast, deterministic unit testing."""

    def search(self, query: str, max_results: int = 5):
        return [
            {
                "title": f"Result 1 for {query}",
                "href": "https://example.com/result-1",
                "body": "This is the first search result summary.",
            },
            {
                "title": f"Result 2 for {query}",
                "href": "https://example.com/result-2",
                "body": "This is the second search result summary.",
            },
        ][:max_results]


def test_web_search_tool_with_mock_provider():
    mock_provider = MockSearchProvider()
    tool = WebSearchTool(provider=mock_provider)

    assert tool.name == "web_search"
    res = tool.execute(query="Python asyncio", max_results=2)

    assert "Web search results for: 'Python asyncio'" in res
    assert "Result 1 for Python asyncio" in res
    assert "https://example.com/result-1" in res
    assert "This is the first search result summary" in res


def test_web_search_empty_query():
    tool = WebSearchTool(provider=MockSearchProvider())
    res = tool.execute(query="   ")
    assert "Error: Search query cannot be empty." in res


def test_web_search_provider_empty_results():
    empty_provider = MagicMock(spec=BaseSearchProvider)
    empty_provider.search.return_value = []
    tool = WebSearchTool(provider=empty_provider)

    res = tool.execute(query="nonexistent term")
    assert "No search results found" in res


def test_tavily_search_missing_key():
    provider = TavilySearchProvider(api_key="")
    with pytest.raises(ValueError) as exc:
        provider.search("test")
    assert "Tavily API key is not configured" in str(exc.value)


def test_fetch_webpage_invalid_url():
    tool = FetchWebpageTool()
    res = tool.execute("invalid-url-without-scheme")
    assert "Error: Invalid URL" in res
    assert "must begin with http:// or https://" in res


def test_fetch_webpage_cleans_html():
    tool = FetchWebpageTool()

    mock_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Sample Article Title</title>
        <style>body { color: red; }</style>
        <script>console.log("noisy script");</script>
      </head>
      <body>
        <nav><a href="#">Home</a></nav>
        <main>
          <h1>Welcome to the Research Lab</h1>
          <p>Autonomous AI agents can gather data and synthesize facts.</p>
        </main>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200

    with patch("requests.get", return_value=mock_response):
        output = tool.execute("https://example.com/article")

        assert "Page Title: Sample Article Title" in output
        assert "Welcome to the Research Lab" in output
        assert "Autonomous AI agents can gather data and synthesize facts." in output
        # Verify stripped junk
        assert "console.log" not in output
        assert "body { color: red; }" not in output
        assert "Copyright 2026" not in output
        assert "Home" not in output


def test_fetch_webpage_truncation_safeguard():
    tool = FetchWebpageTool()
    # Generate 10,000 characters of text
    long_text = "This is important research content. " * 300
    mock_html = f"<html><head><title>Long Document</title></head><body><p>{long_text}</p></body></html>"

    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200

    with patch("requests.get", return_value=mock_response):
        output = tool.execute("https://example.com/long-page")
        assert "Content truncated: showing first" in output
        assert len(output) < 7000


def test_tool_registry_registration():
    registry = ToolRegistry()
    registry.register(WebSearchTool(provider=MockSearchProvider()))
    registry.register(FetchWebpageTool())

    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "web_search" in names
    assert "fetch_webpage" in names
