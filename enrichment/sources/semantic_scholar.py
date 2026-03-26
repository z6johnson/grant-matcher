"""Semantic Scholar API client.

Queries the public Semantic Scholar Academic Graph API to find
author profiles, publications, citation metrics, and h-index.
Free tier: 100 requests/5 minutes without API key.

Docs: https://api.semanticscholar.org/api-docs/
"""

import logging
import os

from .base import BaseSource

logger = logging.getLogger(__name__)

AUTHOR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/author/search"
AUTHOR_URL = "https://api.semanticscholar.org/graph/v1/author/{author_id}"
AUTHOR_PAPERS_URL = "https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"


class SemanticScholarSource(BaseSource):
    source_name = "semantic_scholar"
    # Free tier: 100 requests per 5 minutes = 1 req/3s.
    # With API key: 1 req/s is safe.
    min_request_interval = 3.0
    confidence = 0.75  # good but name disambiguation can be imperfect

    def __init__(self):
        super().__init__()
        api_key = os.getenv("S2_API_KEY", "")
        if api_key:
            self._session.headers.update({"x-api-key": api_key})
            self.min_request_interval = 1.0  # faster with API key

    def fields_provided(self):
        return ["h_index", "recent_publications"]

    def fetch(self, faculty_dict):
        """Search Semantic Scholar for this faculty member."""
        first = faculty_dict.get("first_name", "")
        last = faculty_dict.get("last_name", "")

        author_id, search_hit = self._search_author(first, last)
        if not author_id:
            return None

        return self._fetch_author_data(author_id, first, last, search_hit=search_hit)

    def _search_author(self, first_name, last_name):
        """Search for an author by name, filtering to UCSD affiliation.

        Returns (author_id, search_result_dict) so the caller can use
        h-index and paper count from the search response directly,
        saving an extra API call.
        """
        query = f"{first_name} {last_name}"
        resp = self._get(
            AUTHOR_SEARCH_URL,
            params={
                "query": query,
                "fields": "name,affiliations,paperCount,hIndex",
                "limit": 10,
            },
        )
        if not resp:
            return None, None

        try:
            data = resp.json()
        except ValueError:
            return None, None

        authors = data.get("data") or []
        if not authors:
            return None, None

        # Try to find the UCSD-affiliated match
        ucsd_keywords = [
            "ucsd", "uc san diego", "university of california san diego",
            "scripps", "sio",
        ]
        for author in authors:
            affiliations = author.get("affiliations") or []
            aff_text = " ".join(affiliations).lower()
            if any(kw in aff_text for kw in ucsd_keywords):
                return author.get("authorId"), author

        # If no affiliation match, check if the first result has a
        # reasonable paper count (>5) and name is close enough
        if authors:
            top = authors[0]
            name = (top.get("name") or "").lower()
            full_name = f"{first_name} {last_name}".lower()
            if full_name in name or name in full_name:
                if (top.get("paperCount") or 0) > 5:
                    return top.get("authorId"), top

        return None, None

    def _fetch_author_data(self, author_id, first_name, last_name, search_hit=None):
        """Fetch author profile and recent papers.

        Uses metrics from the search response when available to avoid
        an extra API call for the author profile.
        """
        result = {
            "_source_url": f"https://www.semanticscholar.org/author/{author_id}",
        }

        # Use search result metrics if available (saves one API call).
        # The search response includes hIndex and paperCount when
        # requested via the fields parameter.
        if search_hit and search_hit.get("hIndex") is not None:
            result["h_index"] = search_hit["hIndex"]
            result["paper_count"] = search_hit.get("paperCount")
            result["citation_count"] = search_hit.get("citationCount")
        else:
            # Fall back to a separate author profile fetch
            resp = self._get(
                AUTHOR_URL.format(author_id=author_id),
                params={
                    "fields": "name,affiliations,paperCount,citationCount,hIndex,homepage,externalIds",
                },
            )
            if resp:
                try:
                    author = resp.json()
                    h_index = author.get("hIndex")
                    if h_index is not None:
                        result["h_index"] = h_index
                    result["paper_count"] = author.get("paperCount")
                    result["citation_count"] = author.get("citationCount")
                except ValueError:
                    pass

        # Fetch recent papers
        papers = self._fetch_papers(author_id)
        if papers:
            result["recent_publications"] = papers

        return result if len(result) > 1 else None

    def _fetch_papers(self, author_id):
        """Fetch recent papers for an author."""
        resp = self._get(
            AUTHOR_PAPERS_URL.format(author_id=author_id),
            params={
                "fields": "title,year,venue,citationCount,publicationTypes,journal",
                "limit": 20,
                "sort": "year:desc",  # most recent first
            },
        )
        if not resp:
            return None

        try:
            data = resp.json()
        except ValueError:
            return None

        papers = data.get("data") or []
        publications = []
        for paper in papers:
            pub = {}
            title = paper.get("title")
            if title:
                pub["title"] = title.strip()

            if paper.get("year"):
                pub["year"] = paper["year"]

            # Journal name (prefer journal object, fall back to venue)
            journal = paper.get("journal") or {}
            journal_name = journal.get("name") or paper.get("venue") or ""
            if journal_name:
                pub["journal"] = journal_name

            if pub.get("title"):
                publications.append(pub)

        return publications or None
