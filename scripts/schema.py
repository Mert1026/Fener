import json
import sys
from pathlib import Path

from fener.api import app

path = Path("docs/openapi.json")
if "--check" in sys.argv:
    if json.loads(path.read_text(encoding="utf-8")) != app.openapi():
        raise SystemExit("OpenAPI schema is stale. Run python scripts/manage.py schema")
else:
    path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
