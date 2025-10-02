import json
from pathlib import Path
from datetime import datetime
from typing import Mapping, Any

# Make path relative to this file (not CWD)
BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "data" / "survey.ndjson"

def _default(o: Any):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

def append_json_line(record: Mapping[str, Any]) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default) + "\n")
