"""Paths and the tunable thresholds.

THRESHOLDS is the object of "threshold training": tooling rewrites
LeeAgent/config.json and `thresholds()` prefers it over DEFAULTS, so an
experiment is just a file change plus a gate run.
"""

from __future__ import annotations

import json
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent            # LeeAgent/
REPO_ROOT = ROOT.parent          # AutoTavern/

NIMBLE_BASE = "http://127.0.0.1:18766"
NIMBLE_MODEL = "nimble-9b"

# The cold-path generator reads the same env file as the TavernBench runners.
BENCH_ENV_FILE = Path.home() / ".tavernbench.env"

DEFAULTS = {
    # hot path
    "min_apply_prob": 0.6,     # noul probability for a memory to count as applicable
    "uncertain_band": 0.45,    # below min_apply but above this: "uncertain", logged
    "max_candidates": 16,      # slim candidates sent to Nimble (token budget)
    "max_questions": 8,        # parallel noul applicability questions per turn
    "ask_top_choice": True,    # one extra choice question for priority
    # lookahead
    "fix_positioning": True,
    "positioning_sims": 48,    # combats per candidate arrangement
    # gate / cold path
    "gate_n_games": 40,
    "gate_min_gain": 0.05,     # mean placement-reward gain to accept a memory set
    "max_new_candidates": 3,   # per game from the distiller
    "write_conf": 0.75,        # reserved: Nimble confidence to auto-file a candidate
}


def thresholds() -> dict:
    cfg = dict(DEFAULTS)
    f = ROOT / "config.json"
    if f.is_file():
        cfg.update(json.loads(f.read_text()))
    return cfg
