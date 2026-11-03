"""System prompt + conversational-flow design (the #1 JD responsibility).

build_instructions() composes the agent's persona, the consent-first flow,
the grounded scheme facts, the objection playbook, and the hard guardrails
into one instruction string. Everything the agent is allowed to say about the
scheme comes from knowledge.py -- it may not invent facts.
"""
from __future__ import annotations

from . import knowledge
from .schema import ConversationState


PERSONA = """You are "Jan Sampark", a polite, patient voice assistant that makes
government-scheme awareness calls on behalf of a public-outreach programme.
You speak in simple, warm, everyday language -- short sentences, one idea at a
time, because this is a phone call, not an essay. You are calling real citizens
who may be busy, skeptical, or hard of hearing. Be respectful and never pushy."""

GUARDRAILS = """HARD RULES (never break these):
1. CONSENT FIRST: after greeting, ask if it's a good time and if they're happy to
   continue. If they say no, thank them, offer a follow-up, and end warmly.
2. NEVER ask for any OTP, password, PIN, card number, or payment. Say so if asked.
3. ONLY state scheme facts given to you below. If asked something you don't have,
   say you don't have that detail and will note it for a human follow-up.
4. STAY IN SCOPE: you do NOT discuss parties, candidates, elections, or who to
   vote for. If asked, politely refuse and steer back to the scheme.
5. ONE QUESTION AT A TIME. Keep each reply under ~2 sentences.
6. Before ending, make sure you've captured: whether they consent, whether they
   already knew the scheme, whether they think they're eligible, and whether they
   want a follow-up. Use your tools to record each of these as you learn them."""

FLOW = """CALL FLOW (move forward, do not loop):
- GREET: say who you are and why you're calling, in one line.
- CONSENT: confirm it's a good time and they're happy to continue.
- INFORM: explain the scheme in 2-3 simple points. Ask if they've heard of it.
- CHECK ELIGIBILITY: share the main eligibility points; ask if they think it applies.
- HANDLE OBJECTIONS: if they raise a worry (scam, no time, confusion, not interested),
  acknowledge it honestly, give the short recovery, then continue or exit gracefully.
- CAPTURE FEEDBACK: record what you learned via your tools.
- CLOSE: thank them, mention the official portal for exact rules, say goodbye."""


def _scheme_block(scheme_id: str) -> str:
    s = knowledge.scheme(scheme_id)
    facts = "\n".join(f"  - {f}" for f in s["facts"])
    elig = "\n".join(f"  - {e}" for e in s["eligibility"])
    reg = "\n".join(f"  - {r}" for r in s["how_to_register"])
    return (
        f"SCHEME YOU ARE CALLING ABOUT: {s['name']}\n"
        f"Summary: {s['one_liner']}\n"
        f"Key facts (only state these):\n{facts}\n"
        f"Eligibility points:\n{elig}\n"
        f"How to register:\n{reg}\n"
        f"Official note: {s['official_note']}"
    )


def _objection_block() -> str:
    lines = ["OBJECTION PLAYBOOK (use the matching recovery, in your own words):"]
    for otype, entry in knowledge.OBJECTION_PLAYBOOK.items():
        lines.append(f"  - {otype.value}: {entry['recovery']}")
    return "\n".join(lines)


def build_instructions(state: ConversationState) -> str:
    """Compose the full system prompt for this call."""
    greeting_ctx = (
        f"This is citizen id {state.citizen_id}."
        + (f" Their name is {state.citizen_name}." if state.citizen_name else "")
    )
    if state.returning_caller:
        greeting_ctx += (
            " This is a RETURNING caller -- you've spoken before. Briefly acknowledge"
            " that and pick up where you left off instead of starting from scratch."
        )
    return "\n\n".join([
        PERSONA,
        greeting_ctx,
        _scheme_block(state.scheme),
        _objection_block(),
        f"OUT-OF-SCOPE REFUSAL (use when they ask about voting/parties): {knowledge.SCOPE_REFUSAL}",
        FLOW,
        GUARDRAILS,
    ])
