"""Write docs/openapi.json from the FastAPI app (CI checks it for drift)."""

from __future__ import annotations

import json
from pathlib import Path

from letmegetin.main import app

TARGET = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
