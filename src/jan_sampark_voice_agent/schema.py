"""Typed state for a Jan Sampark call.

- FlowState / ObjectionType: the finite vocabulary the flow and evals share.
- FeedbackRecord: the structured outcome the agent MUST fill (this is what
  "make government programs more effective" actually produces -- data).
- ConversationState: short-term (within-call) memory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar, Optional

from pydantic import BaseModel, Field


class FlowState(str, Enum):
    """Explicit states so the call cannot loop (Repo Interview Coach pattern)."""
    GREET = "greet"
    CONSENT = "consent"
    INFORM = "inform"
    CHECK_ELIGIBILITY = "check_eligibility"
    HANDLE_OBJECTION = "handle_objection"
    CAPTURE_FEEDBACK = "capture_feedback"
    CLOSE = "close"
    ENDED_NO_CONSENT = "ended_no_consent"


class ObjectionType(str, Enum):
    SCAM_FEAR = "scam_fear"
    NO_TIME = "no_time"
    ELIGIBILITY_CONFUSION = "eligibility_confusion"
    NOT_INTERESTED = "not_interested"
    NONE = "none"


class FeedbackRecord(BaseModel):
    """The deliverable of every call. Eval scores field completeness."""
    citizen_id: str
    scheme: str
    consent_given: Optional[bool] = None
    aware_of_scheme: Optional[bool] = None
    self_reported_eligible: Optional[bool] = None
    top_objection: ObjectionType = ObjectionType.NONE
    objection_addressed: bool = False
    wants_followup: Optional[bool] = None
    free_text: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Fields that MUST be set for a call to count as "complete".
    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = (
        "consent_given", "aware_of_scheme", "self_reported_eligible", "wants_followup",
    )

    def completeness(self) -> float:
        """Fraction of required fields captured (0.0 - 1.0). The eval headline."""
        filled = sum(getattr(self, f) is not None for f in self.REQUIRED_FIELDS)
        return filled / len(self.REQUIRED_FIELDS)

    def is_complete(self) -> bool:
        return self.completeness() >= 1.0

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


class ConversationState(BaseModel):
    """Short-term memory held for the duration of one call."""
    citizen_id: str
    citizen_name: str = ""
    scheme: str
    flow: FlowState = FlowState.GREET
    turns: int = 0
    objections_raised: list[ObjectionType] = Field(default_factory=list)
    returning_caller: bool = False
