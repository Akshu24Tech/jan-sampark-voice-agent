"""No-keys demo: drive a full call through the real Jan Sampark brain.

This runs the actual decision modules (objection matching, scope guard,
feedback capture, cross-call memory) on a scripted conversation and prints an
annotated transcript. It does NOT use audio or any API key -- it shows the
agent's *judgement*, which is the part that makes or breaks a voice agent.

Run:  uv run python demo_call.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jan_sampark_voice_agent import knowledge  # noqa: E402
from jan_sampark_voice_agent.memory import CitizenMemory  # noqa: E402
from jan_sampark_voice_agent.schema import (  # noqa: E402
    ConversationState, FeedbackRecord, FlowState, ObjectionType,
)

AGENT = "\033[96mJAN SAMPARK\033[0m"
CITIZEN = "\033[93mCITIZEN   \033[0m"
NOTE = "  \033[90m↳ {}\033[0m"


def agent(line: str) -> None:
    print(f"{AGENT} : {line}")


def citizen(line: str) -> None:
    print(f"{CITIZEN} : {line}")


def note(line: str) -> None:
    print(NOTE.format(line))


def handle_citizen(text: str, rec: FeedbackRecord, state: ConversationState) -> None:
    """Run the real brain on one citizen utterance and react."""
    citizen(text)

    # 1) Responsible-AI scope guard runs first.
    if knowledge.is_out_of_scope(text):
        note("scope guard: OUT OF SCOPE -> refuse + redirect")
        agent(knowledge.SCOPE_REFUSAL)
        return

    # 2) Objection detection (deterministic matcher).
    otype = knowledge.match_objection(text)
    if otype != ObjectionType.NONE:
        note(f"objection detected: {otype.value}")
        state.objections_raised.append(otype)
        rec.top_objection = otype
        rec.objection_addressed = True
        agent(knowledge.recovery_for(otype))
        return

    note("no objection / in scope -> continue flow")


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


def first_call(db: Path) -> None:
    banner("CALL 1  —  citizen 'demo-9821' (new)")
    mem = CitizenMemory(db)
    rec = FeedbackRecord(citizen_id="demo-9821", scheme="pm_kisan")
    state = ConversationState(citizen_id="demo-9821", scheme="pm_kisan")

    s = knowledge.scheme("pm_kisan")
    state.flow = FlowState.GREET
    agent("Namaste! This is Jan Sampark, a government awareness line. "
          "Is this a good time to talk for a minute?")

    state.flow = FlowState.CONSENT
    citizen("Yeah, okay, go on.")
    rec.consent_given = True
    note("record_consent(True)")

    state.flow = FlowState.INFORM
    agent(f"Thank you. I'm calling about {s['name']}. {s['facts'][0]} {s['facts'][1]} "
          "Have you heard of it before?")
    citizen("No, never heard of it.")
    rec.aware_of_scheme = False
    note("record_awareness(already_knew=False)")

    # Objection: scam fear
    handle_citizen("Wait, is this some kind of scam? I don't trust these calls.", rec, state)

    # Eligibility
    state.flow = FlowState.CHECK_ELIGIBILITY
    agent(s["eligibility"][0] + " Do you think it applies to you?")
    citizen("I have two acres, so maybe I qualify?")
    rec.self_reported_eligible = True
    note("record_eligibility(thinks_eligible=True)")

    # Out-of-scope probe
    handle_citizen("By the way, who should I vote for in the election?", rec, state)

    # Close
    state.flow = FlowState.CAPTURE_FEEDBACK
    agent("Understood. Would you like a human to follow up with the exact details?")
    citizen("Yes, that would help.")
    rec.wants_followup = True
    note("record_followup(True)")

    state.flow = FlowState.CLOSE
    agent(f"Great, I've noted that. {s['official_note']} Thank you for your time. Namaste!")

    mem.save(rec)
    print()
    note(f"FLOW: {state.flow.value}  |  objections: {[o.value for o in state.objections_raised]}")
    note(f"FEEDBACK CAPTURED ({rec.completeness():.0%} complete, is_complete={rec.is_complete()}):")
    print(f"      consent={rec.consent_given} aware={rec.aware_of_scheme} "
          f"eligible={rec.self_reported_eligible} objection={rec.top_objection.value} "
          f"followup={rec.wants_followup}")
    note("saved to cross-call memory ✔")


def second_call(db: Path) -> None:
    banner("CALL 2  —  same citizen calls back (cross-call memory)")
    mem = CitizenMemory(db)
    prior = mem.load("demo-9821")
    state = ConversationState(
        citizen_id="demo-9821", scheme="pm_kisan", returning_caller=prior is not None,
    )
    note(f"loaded prior record: returning_caller={state.returning_caller}, "
         f"wanted_followup={prior.wants_followup if prior else None}")
    agent("Namaste again! We spoke earlier about PM-KISAN and you wanted a follow-up. "
          "Shall we pick up where we left off?")
    note("agent resumes with context instead of starting from scratch ✔")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.db"
        first_call(db)
        second_call(db)
        print("\n" + "=" * 64)
        print("  (This is the decision layer — no audio/keys. Live voice needs")
        print("   LiveKit + Deepgram/Groq/Cartesia keys via: agent.py console)")
        print("=" * 64)


if __name__ == "__main__":
    main()
