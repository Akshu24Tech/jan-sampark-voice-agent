"""Deterministic dialog engine for the no-keys demo UI.

In live mode the LLM generates the agent's words. For a keys-free, fully
reproducible demo (and for the Streamlit UI), this module drives the same
conversational *flow* and reuses the same brain (objection matching, scope
guard, grounded scheme facts) with canned, grounded replies.

respond() takes the citizen's message + the live state/record, mutates them,
and returns (agent_reply, debug_note). Nothing here needs audio or an API key.
"""
from __future__ import annotations

import re

from . import knowledge
from .schema import ConversationState, FeedbackRecord, FlowState, ObjectionType

_AFFIRM = {"yes", "yeah", "yep", "yup", "ok", "okay", "sure", "haan", "han",
           "ya", "alright", "fine", "please", "definitely", "ofcourse"}
_NEG = {"no", "nope", "nahi", "nah", "never", "dont", "don't"}


def _polarity(text: str) -> str:
    """Return 'yes' | 'no' | 'unsure' from a short reply."""
    low = text.lower()
    words = set(re.findall(r"[a-z']+", low))
    if "go on" in low or words & _AFFIRM:
        return "yes"
    if words & _NEG:
        return "no"
    return "unsure"


def _faq_answer(text: str, scheme: dict) -> str | None:
    """Answer a grounded factual question without advancing the flow."""
    low = text.lower()
    if any(k in low for k in ("how much", "amount", "money", "rupees", "benefit amount", "how many")):
        return f"{scheme['facts'][0]} {scheme['facts'][1]}"
    if any(k in low for k in ("register", "apply", "sign up", "documents", "how do i get", "enroll")):
        return " ".join(scheme["how_to_register"])
    if "installment" in low:
        return scheme["facts"][1]
    if any(k in low for k in ("when", "date", "deadline", "last date")):
        # Honest "I don't have that" -- anti-hallucination.
        return ("I don't have that exact detail, so I'll note it for a human follow-up. "
                + scheme["official_note"])
    return None


def opening_line(state: ConversationState) -> str:
    scheme = knowledge.scheme(state.scheme)
    if state.returning_caller:
        state.flow = FlowState.CONSENT
        return ("Namaste again! We spoke earlier about " + scheme["name"].split(" (")[0]
                + ". Is this a good time to continue for a minute?")
    state.flow = FlowState.CONSENT
    return ("Namaste! This is Jan Sampark, a government awareness line. I'd like to tell you "
            "about a scheme you may benefit from. Is this a good time to talk for a minute?")


def respond(text: str, state: ConversationState, rec: FeedbackRecord) -> tuple[str, str]:
    """Advance the conversation by one citizen turn. Returns (reply, note)."""
    scheme = knowledge.scheme(state.scheme)
    state.turns += 1

    # 0) Hard loop cap.
    if state.turns > 40:
        state.flow = FlowState.CLOSE
        return ("I've taken enough of your time, thank you. Namaste!", "loop cap reached")

    # 1) Responsible-AI scope guard (always first).
    if knowledge.is_out_of_scope(text):
        return knowledge.SCOPE_REFUSAL, "scope guard: OUT OF SCOPE -> refuse + redirect"

    # 2) Objection handling (can happen in any state).
    otype = knowledge.match_objection(text)
    if otype != ObjectionType.NONE:
        if otype not in state.objections_raised:
            state.objections_raised.append(otype)
        rec.top_objection = otype
        rec.objection_addressed = True
        nxt = " Shall we continue?" if state.flow != FlowState.CLOSE else ""
        return knowledge.recovery_for(otype) + nxt, f"objection detected: {otype.value}"

    # 3) Grounded FAQ (answer without advancing the flow).
    faq = _faq_answer(text, scheme)
    if faq is not None:
        return faq, "grounded FAQ answer (no fact invented)"

    # 4) Flow progression.
    pol = _polarity(text)

    if state.flow == FlowState.CONSENT:
        if pol == "no":
            rec.consent_given = False
            state.flow = FlowState.CLOSE
            return ("No problem at all, I understand. May I note you for a follow-up another time? "
                    "Thank you, Namaste!"), "record_consent(False) -> graceful exit"
        rec.consent_given = True
        state.flow = FlowState.INFORM
        return (f"Thank you. I'm calling about {scheme['name']}. {scheme['facts'][0]} "
                f"{scheme['facts'][1]} Have you heard of this scheme before?"), "record_consent(True)"

    if state.flow == FlowState.INFORM:
        rec.aware_of_scheme = (pol == "yes")
        state.flow = FlowState.CHECK_ELIGIBILITY
        return (f"{scheme['eligibility'][0]} Do you think it might apply to you?"), \
               f"record_awareness(already_knew={rec.aware_of_scheme})"

    if state.flow == FlowState.CHECK_ELIGIBILITY:
        rec.self_reported_eligible = (pol != "no")
        state.flow = FlowState.CAPTURE_FEEDBACK
        return ("Thank you. Would you like a human to follow up with the exact details "
                "and help you register?"), f"record_eligibility(thinks_eligible={rec.self_reported_eligible})"

    if state.flow == FlowState.CAPTURE_FEEDBACK:
        rec.wants_followup = (pol == "yes")
        state.flow = FlowState.CLOSE
        return (f"Noted, thank you. {scheme['official_note']} Have a good day, Namaste!"), \
               f"record_followup({rec.wants_followup}) -> feedback {rec.completeness():.0%} complete"

    # CLOSE / fallthrough.
    return ("Thank you for your time. If you have questions later, the official portal has the "
            "exact details. Namaste!"), "call closed"
