"""The domain brain: scheme facts, objection playbook, scope guard, matchers.

Kept as pure Python (no LiveKit import) so the eval harness can test the
agent's *judgement* -- objection matching, scope refusal, grounded answers --
without spinning up live audio. This is the testable core.

ANTI-HALLUCINATION RULE: the agent may only state scheme facts that appear in
SCHEMES. Anything else -> "I don't have that detail, I'll note it for follow-up."
"""
from __future__ import annotations

import re

from .schema import ObjectionType

# --- Grounded scheme knowledge (illustrative; verify against official source
# before any real use). Keep to stable, widely-published facts only. ---
SCHEMES: dict[str, dict] = {
    "pm_kisan": {
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "one_liner": "An income-support scheme for eligible landholding farmer families.",
        "facts": [
            "It provides income support of 6,000 rupees per year to eligible farmer families.",
            "The amount is paid in three equal installments of 2,000 rupees.",
            "Money is sent directly to the bank account by Direct Benefit Transfer.",
            "It is a Central Government scheme for landholding farmer families.",
        ],
        "eligibility": [
            "Small and marginal landholding farmer families with cultivable land are eligible.",
            "Some groups are excluded, such as income-tax payers, government employees, and higher pension holders.",
        ],
        "how_to_register": [
            "You can register at the official PM-KISAN portal, or at a Common Service Centre, or with your local revenue or agriculture officer.",
            "You will need your Aadhaar, a bank account, and your land record details.",
        ],
        "official_note": "For exact current rules, always check the official PM-KISAN portal.",
    },
}


def scheme(scheme_id: str) -> dict:
    return SCHEMES.get(scheme_id, SCHEMES["pm_kisan"])


# --- Objection playbook (JD: "objection handling") ---
# Each objection: trigger keywords + a calibrated, honest recovery line.
OBJECTION_PLAYBOOK: dict[ObjectionType, dict] = {
    ObjectionType.SCAM_FEAR: {
        "keywords": ["scam", "fraud", "fake", "trust", "real", "cheat", "genuine", "spam"],
        "recovery": (
            "That's a fair concern, and you're right to be careful. I won't ask for "
            "any OTP, password, or payment. This is only an awareness and feedback "
            "call -- you can verify everything yourself on the official government portal."
        ),
    },
    ObjectionType.NO_TIME: {
        "keywords": ["busy", "no time", "not now", "later", "call back", "hurry", "quick"],
        "recovery": (
            "Totally understand. I only need about a minute, and I can note a good time "
            "to follow up instead if you prefer."
        ),
    },
    ObjectionType.ELIGIBILITY_CONFUSION: {
        "keywords": ["eligible", "qualify", "do i get", "am i", "can i apply",
                     "who gets", "gets this", "benefit", "who qualifies"],
        "recovery": (
            "Let me make it simple. I'll tell you the main eligibility points, and if "
            "you're unsure we can mark it for a human follow-up so nobody misses out."
        ),
    },
    ObjectionType.NOT_INTERESTED: {
        "keywords": ["not interested", "don't want", "leave me", "stop", "no thanks", "dont care"],
        "recovery": (
            "No problem at all, I respect that. May I quickly note whether you'd like any "
            "follow-up in future, and then I'll let you go?"
        ),
    },
}


def match_objection(text: str) -> ObjectionType:
    """Classify the citizen's utterance into an objection type (keyword heuristic).

    Deterministic so evals can assert on it. First match by scan order wins;
    order favors the most safety-relevant objection (scam fear) first.
    """
    low = text.lower()
    for otype in (
        ObjectionType.SCAM_FEAR,
        ObjectionType.NOT_INTERESTED,
        ObjectionType.NO_TIME,
        ObjectionType.ELIGIBILITY_CONFUSION,
    ):
        for kw in OBJECTION_PLAYBOOK[otype]["keywords"]:
            # Word-boundary match so "real" doesn't fire inside "really".
            if re.search(r"\b" + re.escape(kw) + r"\b", low):
                return otype
    return ObjectionType.NONE


def recovery_for(otype: ObjectionType) -> str:
    entry = OBJECTION_PLAYBOOK.get(otype)
    return entry["recovery"] if entry else ""


# --- Scope guard (responsible-AI: this is a civic info+feedback line, NOT
# a campaign or persuasion bot). Refuse partisan / voting-advice questions. ---
OUT_OF_SCOPE_TRIGGERS = [
    "who should i vote", "which party", "vote for", "whom to vote",
    "bjp", "congress", "aap", "best candidate", "who will win",
    "election result", "politician", "better party", "support which",
]


def is_out_of_scope(text: str) -> bool:
    low = text.lower()
    return any(trigger in low for trigger in OUT_OF_SCOPE_TRIGGERS)


SCOPE_REFUSAL = (
    "I'm not able to help with anything about voting, parties, or candidates -- "
    "I only share information about government schemes and collect your feedback. "
    "Shall we continue with the scheme?"
)
