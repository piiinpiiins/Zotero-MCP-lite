"""
Semantic Scholar API Client for MCP Zotero.

Provides access to the Semantic Scholar Academic Graph API
for searching papers, retrieving citations/references, and
getting paper recommendations.

API Docs: https://api.semanticscholar.org/api-docs/graph
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict, Any, Optional


# Default fields to request from the API
PAPER_FIELDS = "paperId,title,year,citationCount,abstract,authors,externalIds,venue,url"
CITATION_FIELDS = "paperId,title,year,citationCount,authors,externalIds,venue,url"

# Rate limit: 1 RPS with API key, shared pool without
_last_request_time = 0.0
_MIN_INTERVAL = 1.1  # seconds between requests


class SemanticScholarError(Exception):
    """Custom exception for Semantic Scholar API errors."""
    pass


class SemanticScholarClient:
    """Client for the Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org"
    GRAPH_URL = f"{BASE_URL}/graph/v1"
    RECOMMENDATIONS_URL = f"{BASE_URL}/recommendations/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        global _last_request_time
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_request_time = time.time()

    def _request(self, url: str, method: str = "GET",
                 data: Optional[dict] = None) -> dict:
        """Make an HTTP request to the Semantic Scholar API."""
        self._rate_limit()

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                raise SemanticScholarError(
                    "Rate limited by Semantic Scholar. "
                    "Please set SEMANTIC_SCHOLAR_API_KEY environment variable "
                    "for a dedicated rate limit. "
                    "Get a free key at https://www.semanticscholar.org/product/api#api-key-form"
                )
            raise SemanticScholarError(
                f"Semantic Scholar API error {e.code}: {error_body}"
            )
        except urllib.error.URLError as e:
            raise SemanticScholarError(f"Network error: {e.reason}")

    # ── Search ───────────────────────────────────────────────

    def search_papers(self, query: str, limit: int = 10,
                      year: Optional[str] = None,
                      fields: str = PAPER_FIELDS) -> List[Dict[str, Any]]:
        """
        Search for papers globally.

        Args:
            query: Search query string.
            limit: Max results (1-100).
            year: Optional year filter, e.g. "2020", "2020-2024", "2020-".
            fields: Comma-separated fields to return.

        Returns:
            List of paper dicts.
        """
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": fields,
        }
        if year:
            params["year"] = year

        url = f"{self.GRAPH_URL}/paper/search?{urllib.parse.urlencode(params)}"
        result = self._request(url)
        return result.get("data", [])

    # ── Paper details ────────────────────────────────────────

    def get_paper(self, paper_id: str,
                  fields: str = PAPER_FIELDS) -> Optional[Dict[str, Any]]:
        """
        Get details for a single paper.

        Args:
            paper_id: Semantic Scholar paper ID, DOI (prefix with DOI:),
                      or other external ID.
        """
        encoded_id = urllib.parse.quote(paper_id, safe=":")
        url = f"{self.GRAPH_URL}/paper/{encoded_id}?fields={fields}"
        try:
            return self._request(url)
        except SemanticScholarError:
            return None

    # ── Citations & References ───────────────────────────────

    def get_citations(self, paper_id: str, limit: int = 20,
                      fields: str = CITATION_FIELDS) -> List[Dict[str, Any]]:
        """Get papers that cite this paper."""
        encoded_id = urllib.parse.quote(paper_id, safe=":")
        params = {"fields": fields, "limit": min(limit, 1000)}
        url = f"{self.GRAPH_URL}/paper/{encoded_id}/citations?{urllib.parse.urlencode(params)}"
        result = self._request(url)
        # API returns {"data": [{"citingPaper": {...}}, ...]}
        return [item["citingPaper"] for item in result.get("data", [])
                if item.get("citingPaper")]

    def get_references(self, paper_id: str, limit: int = 20,
                       fields: str = CITATION_FIELDS) -> List[Dict[str, Any]]:
        """Get papers referenced by this paper."""
        encoded_id = urllib.parse.quote(paper_id, safe=":")
        params = {"fields": fields, "limit": min(limit, 1000)}
        url = f"{self.GRAPH_URL}/paper/{encoded_id}/references?{urllib.parse.urlencode(params)}"
        result = self._request(url)
        # API returns {"data": [{"citedPaper": {...}}, ...]}
        return [item["citedPaper"] for item in result.get("data", [])
                if item.get("citedPaper")]

    # ── Recommendations ──────────────────────────────────────

    def get_recommendations(self, paper_ids: List[str], limit: int = 10,
                            fields: str = PAPER_FIELDS) -> List[Dict[str, Any]]:
        """
        Get paper recommendations based on one or more seed papers.

        Args:
            paper_ids: List of Semantic Scholar paper IDs.
            limit: Max recommendations.
        """
        params = {"fields": fields, "limit": min(limit, 500)}
        url = f"{self.RECOMMENDATIONS_URL}/papers/?{urllib.parse.urlencode(params)}"
        data = {"positivePaperIds": paper_ids}
        result = self._request(url, method="POST", data=data)
        return result.get("recommendedPapers", [])


# ── Helper: format paper for display ─────────────────────────

def format_paper_md(paper: Dict[str, Any], index: int = 0) -> str:
    """Format a single paper dict into readable markdown."""
    title = paper.get("title") or "Untitled"
    year = paper.get("year") or "N/A"
    citations = paper.get("citationCount") or 0
    venue = paper.get("venue") or ""
    url = paper.get("url") or ""

    # Authors
    authors = paper.get("authors") or []
    author_names = [a.get("name", "") for a in authors[:5]]
    author_str = ", ".join(author_names)
    if len(authors) > 5:
        author_str += f" et al. ({len(authors)} authors)"

    # External IDs
    ext_ids = paper.get("externalIds") or {}
    doi = ext_ids.get("DOI", "")

    prefix = f"### {index}. " if index else "### "
    md = f"{prefix}{title}\n"
    md += f"- **Year:** {year} | **Citations:** {citations}\n"
    if venue:
        md += f"- **Venue:** {venue}\n"
    if author_str:
        md += f"- **Authors:** {author_str}\n"
    if doi:
        md += f"- **DOI:** `{doi}`\n"
    if url:
        md += f"- **URL:** {url}\n"

    abstract = paper.get("abstract")
    if abstract:
        # Truncate long abstracts
        if len(abstract) > 300:
            abstract = abstract[:300] + "..."
        md += f"- **Abstract:** {abstract}\n"

    return md
