"""Client for the local Nimble System One endpoint (typed judgments only).

Quirks this module owns:
- the Authorization header must be present even on loopback;
- HTTP 429: the single-score GPU queue was full, back off and retry;
- HTTP 400 "Longest prompt has N tokens": one scoring pass exceeded the 2048
  cap (the cap applies per question pass, not to the request sum), so
  `ask_batch` splits the question set in half and merges the answers.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from .config import NIMBLE_BASE, NIMBLE_MODEL

_TOO_LONG = re.compile(r"Longest prompt has (\d+) tokens")


class PromptTooLong(Exception):
    def __init__(self, tokens: int, limit: int = 2048):
        super().__init__(f"longest prompt {tokens} > {limit}")
        self.tokens = tokens
        self.limit = limit


def _post(state, questions, base, model, timeout):
    payload = json.dumps({"state": state, "model": model, "questions": questions}).encode()
    for attempt in range(6):
        req = urllib.request.Request(
            base + "/v1/systemone", data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 429 and attempt < 5:
                time.sleep(1.5 * (attempt + 1))
                continue
            if e.code == 400 and "Longest prompt" in body:
                m = _TOO_LONG.search(body)
                raise PromptTooLong(int(m.group(1)) if m else 0) from None
            raise RuntimeError(f"nimble HTTP {e.code}: {body[:200]}") from None
    raise RuntimeError("nimble kept returning 429")


def ask_batch(state, questions, base=NIMBLE_BASE, model=NIMBLE_MODEL, timeout=180) -> dict:
    """Ask a set of independent questions over one state; auto-split on the token cap."""
    try:
        return _post(state, questions, base, model, timeout)
    except PromptTooLong:
        if len(questions) <= 1:
            raise
        keys = list(questions)
        mid = len(keys) // 2
        a = ask_batch(state, {k: questions[k] for k in keys[:mid]}, base, model, timeout)
        b = ask_batch(state, {k: questions[k] for k in keys[mid:]}, base, model, timeout)
        a["answers"].update(b["answers"])
        a["usage"]["input_tokens"] = (a["usage"].get("input_tokens", 0)
                                      + b["usage"].get("input_tokens", 0))
        for k in ("scoring_ms",):
            a.setdefault("nimble_metrics", {})[k] = max(a["nimble_metrics"].get(k, 0),
                                                        b["nimble_metrics"].get(k, 0))
        a["_splits"] = a.get("_splits", 1) + b.get("_splits", 1)
        return a


def health(base=NIMBLE_BASE) -> dict:
    try:
        with urllib.request.urlopen(base + "/health", timeout=3) as r:
            return json.load(r)
    except Exception:
        return {}
