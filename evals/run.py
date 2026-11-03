"""Jan Sampark eval harness -- produces THE interview number.

Two tiers (Repo Guardian pattern):
  1. Deterministic gate (drives the exit code): objection-matcher accuracy,
     scope-guard accuracy, memory round-trip, and feedback-completeness logic.
  2. Config sanity: latency budget + turn-taking knobs are set.

Run:  uv run python evals/run.py
Exit code 0 only if every deterministic check passes.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make the src package importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jan_sampark_voice_agent import config, knowledge  # noqa: E402
from jan_sampark_voice_agent.memory import CitizenMemory  # noqa: E402
from jan_sampark_voice_agent.schema import FeedbackRecord  # noqa: E402
import scenarios  # noqa: E402


class Scorecard:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{name}: {detail}")

    @property
    def total(self) -> int:
        return self.passed + self.failed


def run() -> int:
    s = Scorecard()

    # --- Tier 1a: objection classification ---
    obj_hits = 0
    for text, expected in scenarios.OBJECTION_CASES:
        got = knowledge.match_objection(text)
        ok = got == expected
        obj_hits += ok
        s.check(f"objection[{expected.value}]", ok, f"'{text}' -> {got.value}")

    # --- Tier 1b: scope guard (responsible AI) ---
    scope_hits = 0
    for text, should_refuse in scenarios.SCOPE_CASES:
        got = knowledge.is_out_of_scope(text)
        ok = got == should_refuse
        scope_hits += ok
        s.check("scope_guard", ok, f"'{text}' expected_refuse={should_refuse} got={got}")

    # --- Tier 1c: feedback completeness logic ---
    for sc in (scenarios.HAPPY_PATH, scenarios.NO_CONSENT):
        rec = FeedbackRecord(citizen_id=sc["citizen_id"], scheme="pm_kisan")
        for field, val in sc["updates"].items():
            setattr(rec, field, val)
        ok = rec.is_complete() == sc["expect_complete"]
        s.check("completeness", ok,
                f"{sc['citizen_id']} completeness={rec.completeness():.2f} complete={rec.is_complete()}")

    # --- Tier 1d: cross-call memory round-trip ---
    with tempfile.TemporaryDirectory() as tmp:
        mem = CitizenMemory(Path(tmp) / "t.db")
        rec = FeedbackRecord(citizen_id="rt-1", scheme="pm_kisan", consent_given=True,
                             aware_of_scheme=True, free_text="prefers Hindi")
        mem.save(rec)
        back = mem.load("rt-1")
        s.check("memory_roundtrip", back is not None and back.free_text == "prefers Hindi",
                f"loaded={back}")
        s.check("memory_returning_flag", mem.has_seen("rt-1") and not mem.has_seen("nope"))

    # --- Tier 2: config sanity ---
    s.check("latency_budget_set", 0 < config.LATENCY_BUDGET_S <= 3.0,
            f"{config.LATENCY_BUDGET_S}s")
    s.check("interruption_tuned", config.MIN_INTERRUPTION_WORDS >= 1 and config.ALLOW_INTERRUPTIONS)
    s.check("preemptive_generation_on", config.PREEMPTIVE_GENERATION)
    s.check("loop_cap_set", config.MAX_TURNS > 0)

    # --- Report ---
    obj_acc = obj_hits / len(scenarios.OBJECTION_CASES)
    scope_acc = scope_hits / len(scenarios.SCOPE_CASES)
    print("=" * 56)
    print("  JAN SAMPARK -- EVAL SCORECARD")
    print("=" * 56)
    print(f"  Objection matcher : {obj_hits}/{len(scenarios.OBJECTION_CASES)}  ({obj_acc:.0%})")
    print(f"  Scope guard       : {scope_hits}/{len(scenarios.SCOPE_CASES)}  ({scope_acc:.0%})")
    print(f"  Checks passed     : {s.passed}/{s.total}")
    print(f"  Latency budget    : {config.LATENCY_BUDGET_S}s (end-of-speech -> first byte)")
    print("=" * 56)
    if s.failures:
        print("  FAILURES:")
        for f in s.failures:
            print(f"   - {f}")
    verdict = "PASS" if s.failed == 0 else "FAIL"
    print(f"  VERDICT: {verdict}")
    print("=" * 56)
    return 0 if s.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
