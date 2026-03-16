"""CLI entry point for the enrichment pipeline.

Usage:
    python -m enrichment.cli --all
    python -m enrichment.cli --faculty-id 42
    python -m enrichment.cli --source ucsd_profile
    python -m enrichment.cli --dry-run --all
    python -m enrichment.cli --status
"""

import argparse
import json
import logging
import sys

from flask import Flask

from db import init_db
from enrichment.pipeline import enrich_all, enrich_faculty, get_enrichment_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    """Create a minimal Flask app for DB access."""
    app = Flask(__name__)
    init_db(app)
    return app


def main():
    parser = argparse.ArgumentParser(
        description="Faculty data enrichment pipeline",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Enrich all faculty members",
    )
    parser.add_argument(
        "--faculty-id", type=int,
        help="Enrich a specific faculty member by ID",
    )
    parser.add_argument(
        "--source", type=str,
        help="Use only this source (ucsd_profile, nih_reporter, pubmed)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch data but do not write to DB",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show enrichment coverage statistics",
    )

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.status:
            status = get_enrichment_status()
            print("\n=== Enrichment Coverage ===")
            print(f"Total faculty:          {status['total_faculty']}")
            print(f"Original interests:     {status['with_original_interests']} "
                  f"({status['coverage_original']}%)")
            print(f"Enriched interests:     {status['with_enriched_interests']} "
                  f"({status['coverage_enriched']}%)")
            print(f"With funded grants:     {status['with_funded_grants']}")
            print(f"With publications:      {status['with_publications']}")
            return

        sources = [args.source] if args.source else None

        if args.faculty_id:
            result = enrich_faculty(
                args.faculty_id,
                sources=sources,
                dry_run=args.dry_run,
            )
            print(json.dumps(result, indent=2, default=str))

        elif args.all:
            results = enrich_all(sources=sources, dry_run=args.dry_run)
            enriched = sum(
                1 for r in results
                if any(
                    s.get("status") == "data_found"
                    for s in r.get("sources", {}).values()
                )
            )
            print(f"\nProcessed {len(results)} faculty, {enriched} enriched.")
            if args.dry_run:
                print("(Dry run — no changes written to database)")

        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
