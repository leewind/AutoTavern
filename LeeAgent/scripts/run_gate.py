"""A/B gate between two memory banks (wrapper over leeagent.gate).

    ../.venv/bin/python scripts/run_gate.py --b memories/candidates.jsonl --n 40
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import gate  # noqa: E402

if __name__ == "__main__":
    gate.main()
