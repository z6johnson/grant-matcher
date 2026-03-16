"""UCSD faculty profile scraper.

Fetches public faculty profile pages from profiles.ucsd.edu to extract
research descriptions, bio text, and lab affiliations.
"""

import logging
import re

from bs4 import BeautifulSoup

from .base import BaseSource

logger = logging.getLogger(__name__)


class UCSDProfileSource(BaseSource):
    source_name = "ucsd_profile"
    min_request_interval = 2.0  # respect the server: 1 req per 2 seconds
    confidence = 1.0  # institutional source — highest confidence

    PROFILES_BASE = "https://profiles.ucsd.edu"

    def fields_provided(self):
        return ["research_interests_enriched", "profile_url"]

    def fetch(self, faculty_dict):
        """Scrape the UCSD profiles page for this faculty member."""
        first = faculty_dict.get("first_name", "")
        last = faculty_dict.get("last_name", "")

        # Try the profiles.ucsd.edu search
        profile_data = self._search_profiles_ucsd(first, last)
        if profile_data:
            return profile_data

        # Fallback: try hwsph directory page scrape
        return self._search_hwsph_directory(first, last)

    def _search_profiles_ucsd(self, first_name, last_name):
        """Search profiles.ucsd.edu for the faculty member."""
        search_url = f"{self.PROFILES_BASE}/search"
        resp = self._get(search_url, params={
            "from": "0",
            "searchtype": "people",
            "searchfor": f"{first_name} {last_name}",
        })
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the profile link that matches this person
        profile_link = None
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            link_text = link.get_text(strip=True).lower()
            full_name = f"{first_name} {last_name}".lower()
            if full_name in link_text and "/profile/" in href:
                profile_link = href if href.startswith("http") else f"{self.PROFILES_BASE}{href}"
                break

        if not profile_link:
            return None

        # Fetch the individual profile page
        resp = self._get(profile_link)
        if not resp:
            return None

        return self._parse_profile_page(resp.text, profile_link)

    def _parse_profile_page(self, html, profile_url):
        """Extract research description from a profiles.ucsd.edu page."""
        soup = BeautifulSoup(html, "html.parser")
        data = {"profile_url": profile_url}

        # Look for research/overview section — common patterns in UCSD profiles
        research_text_parts = []

        for heading in soup.find_all(["h2", "h3", "h4"]):
            heading_text = heading.get_text(strip=True).lower()
            if any(kw in heading_text for kw in ["research", "overview", "biography", "interests"]):
                # Grab sibling elements until the next heading
                for sibling in heading.find_next_siblings():
                    if sibling.name in ("h2", "h3", "h4"):
                        break
                    text = sibling.get_text(strip=True)
                    if text:
                        research_text_parts.append(text)

        # Also check for meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            research_text_parts.append(meta_desc["content"])

        if research_text_parts:
            combined = " ".join(research_text_parts)
            # Clean up whitespace
            combined = re.sub(r"\s+", " ", combined).strip()
            # Truncate to reasonable length
            if len(combined) > 2000:
                combined = combined[:2000]
            data["research_interests_enriched"] = combined

        return data if "research_interests_enriched" in data else None

    def _search_hwsph_directory(self, first_name, last_name):
        """Fallback: search the HWSPH faculty directory for a bio link."""
        url = "https://hwsph.ucsd.edu/people/faculty/faculty-directory.html"
        resp = self._get(url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        full_name = f"{first_name} {last_name}".lower()

        for link in soup.find_all("a", href=True):
            if full_name in link.get_text(strip=True).lower():
                href = link["href"]
                if not href.startswith("http"):
                    href = f"https://hwsph.ucsd.edu{href}"

                detail_resp = self._get(href)
                if detail_resp:
                    return self._parse_profile_page(detail_resp.text, href)

        return None
