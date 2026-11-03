# Jan Sampark — a real-time voice agent for government-scheme awareness & citizen feedback

A consent-first voice AI agent built on **LiveKit Agents (Python)**. It calls a
citizen, explains a government scheme in plain language, **handles objections**
("is this a scam?", "I'm busy", "am I eligible?"), stays strictly in scope
(no politics / no voting advice), and records **structured feedback** that an
outreach programme can act on.

> **Eval headline:** 26/26 deterministic checks pass · objection matcher 10/10 ·
> scope guard 8/8 · latency budget 2.0s (end-of-speech → first audio byte).

Built for a voice-AI role at a political & policy consulting org — the domain
(community outreach + making government programs more effective) is the product,
not a generic restaurant-booking bot.

---

## What it demonstrates (maps 1:1 to the role)

| Responsibility | Where it lives |
|---|---|
| System prompts, agent instructions & conversational flow | `prompts.py` (persona + consent-first flow + guardrails) |
| STT → LLM → TTS pipeline | `agent.py` `_build_session()` — Deepgram · Groq · Cartesia |
| Interruption handling (barge-in) | LiveKit turn-detector + tuned `min_interruption_duration` (`config.py`) |
| Objection handling | `knowledge.py` objection playbook + matcher |
| Latency optimization | preemptive generation + streaming models + metrics logging |
| Conversational memory | within-call `ConversationState` + cross-call SQLite (`memory.py`) |
| Debug / identify conversation failures | `evals/` two-tier harness with a scorecard |

---

## Architecture

```
          ┌─────────── LiveKit AgentSession ───────────┐
 caller → │  Deepgram STT → turn-detector → Groq LLM → │ → Cartesia TTS → caller
 audio    │          ▲ barge-in / interruptions        │     audio
          │          │                                 │
          │   ┌──────┴───────── the "brain" ───────────┴──────┐
          │   │ prompts.py  consent-first flow + guardrails    │
          │   │ knowledge.py objection playbook · scope guard  │
          │   │ schema.py    FlowState · FeedbackRecord        │
          │   │ memory.py    SQLite cross-call feedback store   │
          │   └────────────────────────────────────────────────┘
          └─────────────────────────────────────────────────────┘
                     function tools record every field
```

The **brain** (flow logic, objection classification, scope refusal, feedback
schema, memory) is pure Python with no LiveKit import, so it's unit-tested by
`evals/` without live audio. `agent.py` only wires it to the real-time pipeline.

---

## Try it in 30 seconds (no API keys)

The decision layer runs with zero keys — great for a demo or a screen recording:

```bash
uv sync
uv run streamlit run app.py        # browser chat UI: play the citizen, watch the agent's decisions
uv run python demo_call.py         # scripted call, annotated transcript in the terminal
uv run python evals/run.py         # the eval scorecard (26/26)
```

The UI shows objection detection, the responsible-AI scope refusal, grounded
answers, the feedback record filling up, and cross-call memory on a callback.

---

## Quickstart (full voice, needs keys)

```bash
# 1. install
uv sync

# 2. keys
cp .env.example .env.local   # then fill LIVEKIT_*, DEEPGRAM_API_KEY, GROQ_API_KEY, CARTESIA_API_KEY

# 3. one-time: download the turn-detector + VAD model files
uv run python -m jan_sampark_voice_agent.agent download-files

# 4. talk to it in the terminal (local voice loop)
uv run python -m jan_sampark_voice_agent.agent console

# 5. or connect a room (LiveKit Agents Playground / phone via SIP)
uv run python -m jan_sampark_voice_agent.agent dev

# 6. run the eval harness (the number)
uv run python evals/run.py
```

Free accounts: [LiveKit Cloud](https://cloud.livekit.io) · [Deepgram](https://console.deepgram.com) ·
[Groq](https://console.groq.com) · [Cartesia](https://play.cartesia.ai).

---

## Evaluation

Two tiers (the pattern from Repo Guardian):

1. **Deterministic gate** — drives the exit code. Objection-matcher accuracy,
   scope-guard accuracy, feedback-completeness logic, cross-call memory
   round-trip, and turn-taking/latency config sanity.
2. **Config sanity** — interruption tuning, preemptive generation, loop cap.

`uv run python evals/run.py` prints the scorecard and exits non-zero on any
failure, so it drops straight into CI.

---

## Responsible-AI design

- **Consent first** — the call cannot proceed to the pitch until the citizen agrees.
- **No secrets** — never asks for OTP/PIN/password/payment, and says so if asked.
- **In-scope only** — refuses voting advice, party, and candidate questions
  (`is_out_of_scope` + scope refusal line). This is an awareness-and-feedback
  line, not a persuasion bot.
- **Grounded** — the agent may only state scheme facts from `knowledge.py`.

---

## Honest caveat

The eval harness verifies the agent's **decision logic** (objection
classification, scope refusal, memory, completeness) deterministically. It does
**not** yet score live audio quality, real end-to-end latency on a phone call,
or LLM response wording under load — those need a live LiveKit session with
real keys. The scheme facts in `knowledge.py` are illustrative; verify against
the official PM-KISAN portal before any real deployment.

---

## Layout

```
src/jan_sampark_voice_agent/
  config.py      model stack + latency/turn knobs
  schema.py      FlowState, ObjectionType, FeedbackRecord, ConversationState
  knowledge.py   scheme facts, objection playbook, scope guard, matchers
  prompts.py     system prompt + conversational flow
  memory.py      SQLite cross-call feedback store
  agent.py       LiveKit entrypoint + function tools + latency metrics
evals/
  scenarios.py   labeled objection/scope/full-call cases
  run.py         two-tier scorecard harness
```
