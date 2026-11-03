"""LiveKit entrypoint: wires the STT->LLM->TTS pipeline to the Jan Sampark brain.

Run locally:   uv run python -m jan_sampark_voice_agent.agent console
Connect room:  uv run python -m jan_sampark_voice_agent.agent dev

The conversational judgement lives in knowledge.py / prompts.py (pure Python,
unit-tested by evals/). This file only connects it to real-time audio and
exposes function tools the LLM calls to record structured feedback.
"""
from __future__ import annotations

import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    metrics,
)
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import cartesia, deepgram, groq, silero

try:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
except Exception:  # plugin optional; fall back to VAD-only turn detection
    MultilingualModel = None  # type: ignore

from . import config
from .knowledge import is_out_of_scope
from .memory import CitizenMemory
from .prompts import build_instructions
from .schema import ConversationState, FeedbackRecord, ObjectionType

load_dotenv(".env.local")
logger = logging.getLogger("jan-sampark")


class JanSamparkAgent(Agent):
    """The agent + the tools it uses to record what it learns."""

    def __init__(self, state: ConversationState, record: FeedbackRecord, memory: CitizenMemory):
        super().__init__(instructions=build_instructions(state))
        self.state = state
        self.record = record
        self.memory = memory

    def _persist(self) -> None:
        self.record.touch()
        self.memory.save(self.record)

    @function_tool
    async def record_consent(self, context: RunContext, given: bool):
        """Record whether the citizen agreed to continue the call. Call this right after you ask for consent."""
        self.record.consent_given = given
        self._persist()
        return "noted" if given else "noted; wrap up politely"

    @function_tool
    async def record_awareness(self, context: RunContext, already_knew: bool):
        """Record whether the citizen had already heard of the scheme before this call."""
        self.record.aware_of_scheme = already_knew
        self._persist()
        return "noted"

    @function_tool
    async def record_eligibility(self, context: RunContext, thinks_eligible: bool):
        """Record whether the citizen thinks the scheme applies to them."""
        self.record.self_reported_eligible = thinks_eligible
        self._persist()
        return "noted"

    @function_tool
    async def record_objection(self, context: RunContext, objection: str, addressed: bool):
        """Record an objection the citizen raised (scam_fear, no_time, eligibility_confusion, not_interested) and whether you addressed it."""
        try:
            otype = ObjectionType(objection)
        except ValueError:
            otype = ObjectionType.NONE
        self.record.top_objection = otype
        self.record.objection_addressed = addressed
        if otype != ObjectionType.NONE:
            self.state.objections_raised.append(otype)
        self._persist()
        return "noted"

    @function_tool
    async def record_followup(self, context: RunContext, wants_followup: bool):
        """Record whether the citizen wants a human follow-up later."""
        self.record.wants_followup = wants_followup
        self._persist()
        return "noted"

    @function_tool
    async def add_note(self, context: RunContext, note: str):
        """Save any extra free-text the citizen shared that doesn't fit the other fields."""
        self.record.free_text = (self.record.free_text + " " + note).strip()
        self._persist()
        return "noted"


def _build_session() -> AgentSession:
    """Assemble the STT->LLM->TTS pipeline with the tuned latency/turn knobs."""
    kwargs = dict(
        stt=deepgram.STT(model=config.STT_MODEL),
        llm=groq.LLM(model=config.LLM_MODEL),
        tts=cartesia.TTS(voice=config.TTS_VOICE) if config.TTS_VOICE else cartesia.TTS(),
        vad=silero.VAD.load(),
        allow_interruptions=config.ALLOW_INTERRUPTIONS,
        min_interruption_duration=config.MIN_INTERRUPTION_DURATION,
        min_endpointing_delay=config.MIN_ENDPOINTING_DELAY,
        max_endpointing_delay=config.MAX_ENDPOINTING_DELAY,
        preemptive_generation=config.PREEMPTIVE_GENERATION,
    )
    if MultilingualModel is not None:
        kwargs["turn_detection"] = MultilingualModel()
    return AgentSession(**kwargs)


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # Identify the caller. In a real deployment this comes from the dialed number /
    # SIP metadata; for the demo we key on the room name.
    citizen_id = ctx.room.name or "demo-citizen"

    memory = CitizenMemory()
    prior = memory.load(citizen_id)
    record = prior or FeedbackRecord(citizen_id=citizen_id, scheme=config.DEFAULT_SCHEME)
    state = ConversationState(
        citizen_id=citizen_id,
        scheme=record.scheme,
        returning_caller=prior is not None,
    )

    session = _build_session()

    # --- Latency instrumentation (JD: "latency optimization") ---
    usage = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage.collect(ev.metrics)

    agent = JanSamparkAgent(state=state, record=record, memory=memory)
    await session.start(agent=agent, room=ctx.room)

    opener = (
        "Greet the citizen as Jan Sampark in one short line, say you're calling about a "
        "government scheme, and ask if it's a good time to talk for a minute."
    )
    if state.returning_caller:
        opener = (
            "This is a returning caller. Warmly acknowledge you spoke before, then ask if "
            "it's a good time to continue for a minute."
        )
    await session.generate_reply(instructions=opener)


def main() -> None:
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
