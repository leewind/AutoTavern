"""Hot path: code prefilter -> Nimble applicability + priority, once per turn.

Token budget (measured): state ~250 + 16 slim candidates ~200 + 8 noul + 1
choice ~1000 => ~1500 of the 2048 per-pass cap. ask_batch() splits if a
generated situation ever pushes a pass over.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import memory
from . import nimble
from .facts import render_state


@dataclass
class Retrieval:
    candidates: list = field(default_factory=list)   # prefetched ids
    matched: list = field(default_factory=list)      # [(memory, prob)] sorted by prob
    top: str = ""                                    # choice: most important id ("none"/"")
    uncertain: list = field(default_factory=list)    # [(memory, prob)] in the uncertain band
    nimble_ms: float = 0.0
    tokens: int = 0
    splits: int = 0


def retrieve(store: list, view: dict, facts: dict, th: dict, base: str = nimble.NIMBLE_BASE) -> Retrieval:
    r = Retrieval()
    cands = memory.prefilter(store, facts, th["max_candidates"])
    r.candidates = [m["id"] for m in cands]
    if not cands or facts.get("pending"):
        return r

    state = {"game": render_state(view),
             "candidates": [memory.slim(m) for m in cands]}
    qs = {}
    for k, m in enumerate(cands[:th["max_questions"]]):
        qs[f"app_{m['id']}"] = {
            "type": "noul",
            "instructions": (f"Memory candidate {m['id']} is at `candidates[{k}]`. "
                             f"Is its situation present in `game` right now?"),
            "criteria": {"true": "applies to the current game state",
                         "false": "does not apply now"}}
    if th["ask_top_choice"] and len(cands) > 1:
        qs["top"] = {
            "type": "choice",
            "instructions": "Which single memory candidate is the most important "
                            "to act on in the current `game` state?",
            "criteria": {m["id"]: m["situation"] for m in cands} | {"none": "No candidate applies now"}}

    out = nimble.ask_batch(state, qs, base=base)
    r.nimble_ms = out.get("nimble_metrics", {}).get("scoring_ms", 0.0)
    r.tokens = out.get("usage", {}).get("input_tokens", 0)
    r.splits = out.get("_splits", 1)
    r.top = out["answers"].get("top", {}).get("choice", "")

    scored = []
    for m in cands:
        a = out["answers"].get(f"app_{m['id']}")
        if a is not None:
            scored.append((m, float(a["noul"])))
    r.matched = sorted([x for x in scored if x[1] >= th["min_apply_prob"]],
                       key=lambda x: -x[1])
    r.uncertain = sorted([x for x in scored
                          if th["uncertain_band"] <= x[1] < th["min_apply_prob"]],
                         key=lambda x: -x[1])
    return r
