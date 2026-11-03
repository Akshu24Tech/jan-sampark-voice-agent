"""Central config: model stack + latency/turn-taking knobs.

One place to tune the STT->LLM->TTS pipeline so the latency story is
explicit and reviewable (JD: "latency optimization").
"""
from __future__ import annotations

import os

# --- Model stack (chosen for low latency + free/cheap tiers) ---
# STT: Deepgram Nova (streaming). LLM: Groq (fast first-token).
# TTS: Cartesia (streaming). Turn detection: LiveKit turn-detector model.
STT_MODEL = os.getenv("JS_STT_MODEL", "nova-3")
# Groq model id. gpt-oss-20b: fast, reasoning kept in a separate field (not
# spoken). Run `uv run python -m jan_sampark_voice_agent.list_models` or check
# console.groq.com for what your key can access; override with JS_LLM_MODEL.
LLM_MODEL = os.getenv("JS_LLM_MODEL", "openai/gpt-oss-20b")
TTS_VOICE = os.getenv("JS_TTS_VOICE", "")  # Cartesia voice id; empty = plugin default

# --- Turn-taking / interruption knobs (JD: "interruption handling") ---
# Tuned so short backchannel ("haan", "mm-hmm", "ok") does NOT cut the
# agent, but a real interjection does. See LiveKit turn-detection docs.
ALLOW_INTERRUPTIONS = True
MIN_INTERRUPTION_DURATION = 0.5  # seconds of speech before we yield the turn
MIN_INTERRUPTION_WORDS = 2       # words before a detected speech = interruption
MIN_ENDPOINTING_DELAY = 0.4      # min wait before deciding the user finished
MAX_ENDPOINTING_DELAY = 4.0      # upper bound for slower speakers

# --- Latency optimization (JD: "latency optimization") ---
# Speculatively start the LLM before end-of-turn is confirmed.
PREEMPTIVE_GENERATION = True

# Turn-latency budget we hold ourselves to in evals (end-of-user-speech
# -> first audio byte out). Used as the pass/fail threshold.
LATENCY_BUDGET_S = 2.0

# --- Conversation guardrails ---
MAX_TURNS = 40  # hard cap so a call can never loop forever
DEFAULT_SCHEME = os.getenv("JS_SCHEME", "pm_kisan")
