#!/usr/bin/env python3
"""Check enrichment status across all 3 faculties."""

import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

FACULTIES = {
    "HWSPH (Public Health)": os.path.join(DATA_DIR, "faculty.json"),
    "SIO (Scripps Oceanography)": os.path.join(DATA_DIR, "sio_faculty.json"),
    "Jacobs (Engineering)": os.path.join(DATA_DIR, "jacobs_faculty.json"),
}

FIELDS = [
    ("research_interests_enriched", "Enriched Interests"),
    ("expertise_keywords", "Expertise Keywords"),
    ("methodologies", "Methodologies"),
    ("disease_areas", "Disease Areas"),
    ("populations", "Populations"),
    ("funded_grants", "Funded Grants"),
    ("recent_publications", "Recent Publications"),
    ("orcid", "ORCID"),
    ("h_index", "H-Index"),
    ("profile_url", "Profile URL"),
    ("email", "Email"),
]

SEP = "=" * 60
grand_total = 0
grand_enriched = 0

for name, path in FACULTIES.items():
    with open(path) as f:
        data = json.load(f)
    fac = data["faculty"]
    total = len(fac)

    with_enriched_interests = sum(1 for f in fac if f.get("research_interests_enriched"))
    grand_total += total
    grand_enriched += with_enriched_interests

    timestamps = [f["last_enriched"] for f in fac if f.get("last_enriched")]
    latest = max(timestamps) if timestamps else "N/A"
    never_enriched = total - len(timestamps)

    print(f"\n{SEP}")
    print(f"{name} -- {total} faculty")
    print(SEP)
    print(f"  Last enrichment run:  {latest}")
    print(f"  Never enriched:       {never_enriched}")
    print()

    for field, label in FIELDS:
        count = sum(1 for f in fac if f.get(field))
        pct = count / total * 100 if total else 0
        filled = int(pct / 2)
        bar = "#" * filled + "." * (50 - filled)
        print(f"  {label:25s} {count:4d}/{total:4d} ({pct:5.1f}%) |{bar}|")

    incomplete = sum(1 for f in fac
                     if f.get("last_enriched") and not f.get("research_interests_enriched"))
    print(f"\n  Processed but missing enriched interests: {incomplete}")

# Log analysis
print(f"\n{SEP}")
print("ENRICHMENT LOG ANALYSIS")
print(SEP)
log_path = os.path.join(DATA_DIR, "enrichment_log.json")
with open(log_path) as f:
    log = json.load(f)
print(f"  Total log entries: {len(log)}")

if log:
    dates = [e.get("retrieved_at", "")[:10] for e in log if e.get("retrieved_at")]
    date_counts = Counter(dates)
    print("  Entries by date:")
    for d in sorted(date_counts.keys()):
        print(f"    {d}: {date_counts[d]} entries")

    sources = Counter(e.get("source_name", "unknown") for e in log)
    print("  Entries by source:")
    for s, c in sources.most_common():
        print(f"    {s:25s} {c}")

print(f"\n{SEP}")
print("OVERALL SUMMARY")
print(SEP)
missing = grand_total - grand_enriched
print(f"  Total faculty across 3 schools:  {grand_total}")
print(f"  With enriched interests:         {grand_enriched} ({grand_enriched/grand_total*100:.1f}%)")
print(f"  Without enriched interests:      {missing} ({missing/grand_total*100:.1f}%)")

# Completion evaluation
print(f"\n{SEP}")
print("COMPLETION EVALUATION")
print(SEP)
pct = grand_enriched / grand_total
if pct >= 0.90:
    print("  STATUS: COMPLETE -- enrichment coverage >= 90%")
elif pct >= 0.70:
    print("  STATUS: MOSTLY COMPLETE -- enrichment coverage >= 70%")
elif pct >= 0.50:
    print("  STATUS: PARTIAL -- enrichment coverage >= 50%")
else:
    print("  STATUS: INCOMPLETE -- enrichment coverage < 50%")
