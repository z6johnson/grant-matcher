"""NIH RePORTER API client.

Queries the public NIH RePORTER API to find grants associated with
a faculty member. No API key required.
Docs: https://api.reporter.nih.gov/
"""

import logging

from .base import BaseSource

logger = logging.getLogger(__name__)

API_BASE = "https://api.reporter.nih.gov/v2/projects/search"


class NIHReporterSource(BaseSource):
    source_name = "nih_reporter"
    min_request_interval = 1.0
    confidence = 0.8  # verified federal records

    def fields_provided(self):
        return ["funded_grants"]

    def fetch(self, faculty_dict):
        """Search NIH RePORTER for grants where this person is PI."""
        first = faculty_dict.get("first_name", "")
        last = faculty_dict.get("last_name", "")

        payload = {
            "criteria": {
                "pi_names": [
                    {"first_name": first, "last_name": last}
                ],
                "org_names": ["UNIVERSITY OF CALIFORNIA SAN DIEGO"],
            },
            "offset": 0,
            "limit": 25,
            "sort_field": "project_start_date",
            "sort_order": "desc",
        }

        resp = self._post(API_BASE, json=payload)
        if not resp:
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Invalid JSON from NIH RePORTER for %s %s", first, last)
            return None

        results = data.get("results") or []
        if not results:
            return None

        grants = []
        for project in results:
            grant = {
                "title": project.get("project_title", "").strip(),
                "abstract": (project.get("abstract_text") or "")[:500],
                "agency": project.get("agency_ic_fundings", [{}])[0].get("name", "NIH")
                if project.get("agency_ic_fundings")
                else "NIH",
                "amount": project.get("award_amount"),
                "start_date": project.get("project_start_date"),
                "end_date": project.get("project_end_date"),
                "project_number": project.get("project_num", ""),
            }
            # Extract co-PIs
            pi_list = project.get("principal_investigators") or []
            co_pis = [
                f"{pi.get('first_name', '')} {pi.get('last_name', '')}".strip()
                for pi in pi_list
                if pi.get("last_name", "").lower() != last.lower()
            ]
            if co_pis:
                grant["co_pis"] = co_pis

            grants.append(grant)

        return {
            "funded_grants": grants,
            "_source_url": f"{API_BASE} (PI: {first} {last})",
        }
