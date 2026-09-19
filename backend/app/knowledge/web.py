import html
import json
import re
import gzip
from html.parser import HTMLParser
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


USER_AGENT = "Fraiday/0.1"


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def _fetch(url, timeout=10):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        },
    )

    with urlopen(request, timeout=timeout) as response:
        payload = response.read(500_000)
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            payload = gzip.decompress(payload)
        return payload.decode("utf-8", "replace")


def _page_text(url):
    try:
        parser = _TextParser()
        parser.feed(_fetch(url, 8))
        return html.unescape(" ".join(parser.parts))[:12000]
    except Exception:
        return ""


def _github_search(query, max_results=3):
    """
    Lightweight public GitHub code/documentation search fallback.

    GitHub's public API can be queried without authentication for modest
    request rates. We use it only as a research source, not as an execution
    dependency.
    """

    url = (
        "https://api.github.com/search/repositories"
        "?q=" + quote_plus(query)
        + "&sort=stars&order=desc&per_page=" + str(max_results)
    )

    raw = _fetch(url, 10)
    data = json.loads(raw)

    results = []

    for item in data.get("items", [])[:max_results]:
        name = item.get("full_name") or item.get("name") or "GitHub repository"
        description = item.get("description") or ""
        html_url = item.get("html_url") or ""

        content = (
            f"Repository: {name}\n"
            f"Description: {description}\n"
            f"URL: {html_url}\n"
            f"Language: {item.get('language') or 'unknown'}\n"
            f"Stars: {item.get('stargazers_count', 0)}"
        )

        results.append(
            {
                "title": name,
                "url": html_url,
                "content": content,
                "source": "github",
                "source_type": "official",
            }
        )

    return results


def _python_docs_search(query):
    """
    Research source for Python documentation.

    This is intentionally narrow and deterministic. If the objective is
    Python-related, official Python documentation is more useful than
    scraping a general search engine.
    """

    q = query.lower()

    python_terms = (
        "python",
        "pip",
        "asyncio",
        "fastapi",
        "django",
        "pytest",
        "python version",
        "python feature",
    )

    if not any(term in q for term in python_terms):
        return []

    urls = [
        "https://docs.python.org/3/",
        "https://www.python.org/downloads/",
    ]

    results = []

    for url in urls:
        text = _page_text(url)

        if text:
            results.append(
                {
                    "title": "Official Python documentation",
                    "url": url,
                    "content": text,
                    "source": "python.org",
                    "source_type": "official",
                }
            )

    return results


def research_web(query: str, max_results: int = 3):
    """
    Acquire external knowledge without relying on DuckDuckGo's HTML scraper.

    Provider order:

        1. Python official documentation for Python-related questions
        2. GitHub public repository search as a general technical fallback

    Each provider is isolated so a failure from one source does not crash
    the entire workflow.
    """

    errors = []

    try:
        results = _python_docs_search(query)

        if results:
            return {
                "success": True,
                "provider": "python.org",
                "results": results[:max_results],
                "errors": errors,
            }
    except Exception as exc:
        errors.append(
            {
                "provider": "python.org",
                "error": str(exc),
            }
        )

    try:
        results = _github_search(query, max_results)

        if results:
            return {
                "success": True,
                "provider": "github",
                "results": results[:max_results],
                "errors": errors,
            }
    except Exception as exc:
        errors.append(
            {
                "provider": "github",
                "error": str(exc),
            }
        )

    return {
        "success": False,
        "provider": None,
        "results": [],
        "errors": errors,
    }
