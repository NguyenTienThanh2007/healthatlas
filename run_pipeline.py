from __future__ import annotations

import json
import sys

from sqlalchemy.exc import OperationalError

from pipeline.config import get_settings
from pipeline.jobs.full_refresh import run_full_refresh


def main() -> int:
    settings = get_settings()

    try:
        summary = run_full_refresh(settings)
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}\n")
        return 1
    except OperationalError as exc:
        print(
            "\nERROR: Could not connect to PostgreSQL.\n"
            "Check POSTGRES_URL in .env and make sure "
            "PostgreSQL is running.\n"
        )
        print(exc)
        return 2
    except Exception as exc:
        print(
            f"\nERROR: Pipeline failed: {exc}\n"
        )
        return 3

    print("\n=== HEALTHATLAS PIPELINE SUMMARY ===")
    print(
        json.dumps(
            summary,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
