#!/usr/bin/env python3
"""Check enrichment status across all 3 faculties.

Reports per-school field coverage, identifies never-enriched faculty,
flags data-quality issues, and evaluates overall completeness.
"""

import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

FACULTIES = {
    "HWSPH (Public Health)": ("hwsph", os.path.join(DATA_DIR, "faculty.json")),
    "SIO (Scripps Oceanography)": ("sio", os.path.join(DATA_DIR, "sio_faculty.json")),
    "Jacobs (Engineering)": ("jacobs", os.path.join(DATA_DIR, "jacobs_faculty.json")),
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
grand_never_enriched = 0
all_issues = []

for name, (school_key, path) in FACULTIES.items():
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
    grand_never_enriched += never_enriched

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

    # --- Detailed audit checks ---

    # Never-enriched faculty listing
    if never_enriched > 0:
        print(f"\n  Never-enriched faculty ({never_enriched}):")
        never_list = [(i, f) for i, f in enumerate(fac) if not f.get("last_enriched")]
        for i, f in never_list[:15]:
            dept = f.get("department_eah") or f.get("department") or ""
            print(f"    [{i:3d}] {f.get('first_name', '?'):15s} {f.get('last_name', '?'):20s} | {dept}")
        if len(never_list) > 15:
            print(f"    ... and {len(never_list) - 15} more")

        # Detect time-budget cutoff pattern
        enriched_indices = set(i for i, f in enumerate(fac) if f.get("last_enriched"))
        missing_indices = sorted(set(range(total)) - enriched_indices)
        if missing_indices:
            # Find the longest contiguous tail of missing indices ending at the last index
            contiguous_from = max(missing_indices)
            for idx in reversed(missing_indices):
                if idx == contiguous_from or idx == contiguous_from - 1:
                    contiguous_from = idx
            tail_len = max(missing_indices) - contiguous_from + 1
            if tail_len > never_enriched * 0.5:
                all_issues.append(
                    f"{name}: Time-budget cutoff likely -- {tail_len} faculty "
                    f"from index {contiguous_from} onward never processed"
                )

    # Faculty enriched but with zero enriched interests (normalizer failure)
    zero_interests = [(i, f) for i, f in enumerate(fac)
                      if f.get("last_enriched")
                      and not f.get("research_interests_enriched")
                      and not f.get("research_interests")]
    if zero_interests:
        all_issues.append(
            f"{name}: {len(zero_interests)} faculty enriched but have NO interests "
            f"(original or enriched) -- LLM normalizer had no input to synthesize from"
        )

    # Duplicate names
    names = [f"{f.get('first_name', '')} {f.get('last_name', '')}" for f in fac]
    name_counts = Counter(names)
    dupes = {n: c for n, c in name_counts.items() if c > 1}
    if dupes:
        for dup_name, count in dupes.items():
            all_issues.append(f"{name}: Duplicate name \"{dup_name}\" appears {count} times")

    # Missing names
    nameless = [(i, f) for i, f in enumerate(fac)
                if not f.get("first_name") or not f.get("last_name")]
    if nameless:
        all_issues.append(f"{name}: {len(nameless)} faculty missing first or last name")

    # Low h-index coverage (Semantic Scholar may be underperforming)
    h_count = sum(1 for f in fac if f.get("h_index"))
    if h_count < total * 0.2:
        all_issues.append(
            f"{name}: H-index only populated for {h_count}/{total} "
            f"({h_count/total*100:.0f}%) -- Semantic Scholar source may be rate-limited"
        )

    # Low profile_url coverage
    url_count = sum(1 for f in fac if f.get("profile_url"))
    if url_count < total * 0.5:
        all_issues.append(
            f"{name}: Profile URL only populated for {url_count}/{total} "
            f"({url_count/total*100:.0f}%)"
        )

# Log analysis
print(f"\n{SEP}")
print("ENRICHMENT LOG ANALYSIS")
print(SEP)
log_path = os.path.join(DATA_DIR, "enrichment_log.jsonl")
if os.path.exists(log_path):
    log = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    log.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
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
else:
    print("  Log file not found (enrichment_log.jsonl) -- will be created on next enrichment run")

print(f"\n{SEP}")
print("OVERALL SUMMARY")
print(SEP)
missing = grand_total - grand_enriched
print(f"  Total faculty across 3 schools:  {grand_total}")
print(f"  With enriched interests:         {grand_enriched} ({grand_enriched/grand_total*100:.1f}%)")
print(f"  Without enriched interests:      {missing} ({missing/grand_total*100:.1f}%)")
print(f"  Never enriched (no timestamp):   {grand_never_enriched}")

# Audit issues
if all_issues:
    print(f"\n{SEP}")
    print("AUDIT ISSUES")
    print(SEP)
    for i, issue in enumerate(all_issues, 1):
        print(f"  {i}. {issue}")

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
