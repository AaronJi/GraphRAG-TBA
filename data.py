"""Project paths and JSON Lines input."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]
