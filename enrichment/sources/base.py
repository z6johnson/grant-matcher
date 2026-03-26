"""Base class for enrichment data sources."""

import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """Abstract base class for all enrichment sources.

    Subclasses implement fetch() and return raw data dicts.
    Rate limiting and error handling are provided by this base.
    """

    # Override in subclasses
    source_name = "base"
    min_request_interval = 1.0  # seconds between requests
    confidence = 0.5

    def __init__(self):
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "UCSD-GrantMatch/1.0 (academic research tool; "
                          "contact: hwsph-grants@ucsd.edu)",
        })

    def _rate_limit(self):
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, url, **kwargs):
        """Rate-limited GET request with error handling and 429 retry."""
        self._rate_limit()
        try:
            resp = self._session.get(url, timeout=30, **kwargs)
            # Retry once on rate limit (429) with backoff
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                logger.info("Rate limited by %s, retrying in %ds", url, retry_after)
                time.sleep(retry_after)
                self._last_request_time = time.time()
                resp = self._session.get(url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning("Request to %s failed: %s", url, e)
            return None

    def _post(self, url, **kwargs):
        """Rate-limited POST request with error handling."""
        self._rate_limit()
        try:
            resp = self._session.post(url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning("POST to %s failed: %s", url, e)
            return None

    @abstractmethod
    def fetch(self, faculty_dict):
        """Fetch enrichment data for a faculty member.

        Args:
            faculty_dict: Dict with at least first_name, last_name, email.

        Returns:
            Dict of extracted data, or None if no data found.
            Keys should map to Faculty model fields.
        """

    @abstractmethod
    def fields_provided(self):
        """Return list of Faculty field names this source can populate."""
