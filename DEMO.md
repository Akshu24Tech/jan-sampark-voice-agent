# Jan Sampark — 60–90s Demo Script

Goal: one screen recording that proves it works and hits every JD bullet. Record
with OBS / the Windows Game Bar (Win+G) capturing screen **and** mic.

## Before you record
1. `cp .env.example .env.local` and fill all keys (LiveKit, Deepgram, Groq, Cartesia).
2. Warm the terminal: `uv run python evals/run.py` (shows the green scorecard).
3. Start the agent: `uv run python -m jan_sampark_voice_agent.agent console`.

## The run of show (speak these as the "citizen")
| # | You say (as citizen) | What to show it does |
|---|---|---|
| 1 | *(let it greet)* | Agent introduces itself as Jan Sampark, asks consent |
| 2 | "Yes, go ahead." | It explains the scheme in 2–3 simple points |
| 3 | *(interrupt mid-sentence)* "wait—" | **Barge-in**: it stops and listens |
| 4 | "Is this a scam?" | **Objection handling**: honest recovery, "no OTP/password ever" |
| 5 | "Am I eligible with two acres?" | Grounded eligibility answer |
| 6 | "Who should I vote for?" | **Scope guard**: politely refuses, steers back |
| 7 | "Okay, you can follow up later." | Records followup = yes; closes politely |

## After the call
- Show `evals/run.py` scorecard on screen: **26/26 · matcher 10/10 · scope 8/8**.
- Optional: show the SQLite row written for the citizen (cross-call memory).

## The one line to say over the recording
"Full STT→LLM→TTS pipeline on LiveKit — barge-in, objection handling, a
responsible-AI scope guard, and an eval harness. Built in the company's own
domain."

## Where to post
- Pin the repo on GitHub, link from the portfolio.
- A short LinkedIn build-in-public post (run the draft through `slop_check.py` first).
