#!/usr/bin/env python3
"""Remove inactive faculty (eah_active=false) from all data files.

One-time cleanup script. After this, the data files contain only active
faculty, and enrichment counts are no longer skewed by inactive records.
"""

import json
import os
import tempfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

FILES = {
    "HWSPH": os.path.join(DATA_DIR, "faculty.json"),
    "SIO": os.path.join(DATA_DIR, "sio_faculty.json"),
    "Jacobs": os.path.join(DATA_DIR, "jacobs_faculty.json"),
}


def save_json_atomic(data, path):
    dir_path = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


def main():
    total_removed = 0

    for name, path in FILES.items():
        with open(path) as f:
            data = json.load(f)

        before = len(data["faculty"])
        removed = [f for f in data["faculty"] if f.get("eah_active") is False]
        kept = [f for f in data["faculty"] if f.get("eah_active") is not False]

        data["faculty"] = kept
        save_json_atomic(data, path)

        total_removed += len(removed)
        print(f"{name}: {before} -> {len(kept)} ({len(removed)} inactive removed)")

        if removed:
            for f in sorted(removed, key=lambda x: x.get("last_name", "")):
                enriched = "enriched" if f.get("research_interests_enriched") else "empty"
                print(f"  - {f.get('first_name', '')} {f.get('last_name', '')} ({enriched})")

    print(f"\nTotal removed: {total_removed}")


if __name__ == "__main__":
    main()
