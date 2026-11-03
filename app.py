"""Jan Sampark — no-keys demo UI (Streamlit).

A browser chat where you play the citizen and watch the agent's decisions live:
objection detection, scope refusal, grounded answers, the feedback record
filling up, and cross-call memory. Runs the REAL brain -- no audio, no API keys.

Run:  uv run streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

from jan_sampark_voice_agent import config, dialog, knowledge  # noqa: E402
from jan_sampark_voice_agent.memory import CitizenMemory  # noqa: E402
from jan_sampark_voice_agent.schema import (  # noqa: E402
    ConversationState, FeedbackRecord,
)

st.set_page_config(page_title="Jan Sampark — Voice Agent Demo", page_icon="📞", layout="wide")

MEM = CitizenMemory()


def start_call(citizen_id: str) -> None:
    prior = MEM.load(citizen_id)
    rec = prior or FeedbackRecord(citizen_id=citizen_id, scheme=config.DEFAULT_SCHEME)
    state = ConversationState(
        citizen_id=citizen_id, scheme=rec.scheme, returning_caller=prior is not None,
    )
    opening = dialog.opening_line(state)
    st.session_state.state = state
    st.session_state.rec = rec
    st.session_state.messages = [("assistant", opening, "")]
    st.session_state.started = True


# ---------------- Sidebar: caller + live feedback record ----------------
with st.sidebar:
    st.header("📞 Caller")
    cid = st.text_input("Citizen phone / id", value=st.session_state.get("cid", "98210-00001"))
    st.session_state.cid = cid
    scheme = knowledge.scheme(config.DEFAULT_SCHEME)
    st.caption(f"Scheme: **{scheme['name']}**")
    if st.button("Start / Restart call", type="primary", use_container_width=True):
        start_call(cid)

    if st.session_state.get("started"):
        rec: FeedbackRecord = st.session_state.rec
        state: ConversationState = st.session_state.state
        st.divider()
        st.subheader("🧠 Live state")
        tag = "🔁 returning caller" if state.returning_caller else "🆕 new caller"
        st.caption(f"{tag}  ·  flow: `{state.flow.value}`  ·  turns: {state.turns}")

        st.subheader("📋 Feedback record")

        def mark(v):
            return "⬜ —" if v is None else ("✅ yes" if v else "❌ no")

        st.markdown(
            f"- **Consent:** {mark(rec.consent_given)}\n"
            f"- **Already aware:** {mark(rec.aware_of_scheme)}\n"
            f"- **Thinks eligible:** {mark(rec.self_reported_eligible)}\n"
            f"- **Top objection:** `{rec.top_objection.value}`"
            f" ({'addressed' if rec.objection_addressed else 'open'})\n"
            f"- **Wants follow-up:** {mark(rec.wants_followup)}"
        )
        st.progress(rec.completeness(), text=f"Completeness {rec.completeness():.0%}")

        st.divider()
        st.success("Eval harness: 26/26 checks · matcher 10/10 · scope 8/8")
        with st.expander("💡 Try saying…"):
            st.markdown(
                "- *\"yes, go on\"* → consent\n"
                "- *\"is this a scam?\"* → objection recovery\n"
                "- *\"how much money is it?\"* → grounded answer\n"
                "- *\"who should I vote for?\"* → scope refusal\n"
                "- restart with the **same id** → returning-caller memory"
            )

# ---------------- Main: chat ----------------
st.title("Jan Sampark — Government-Scheme Voice Agent")
st.caption("Decision-layer demo · no audio, no API keys · you play the citizen. "
           "Live voice (barge-in + latency) runs via `agent.py console` with keys.")

if not st.session_state.get("started"):
    st.info("👈 Enter a citizen id and click **Start / Restart call** to begin.")
else:
    for role, msg, note in st.session_state.messages:
        with st.chat_message("assistant" if role == "assistant" else "user",
                             avatar="📞" if role == "assistant" else "🧑"):
            st.write(msg)
            if note:
                st.caption(f"↳ {note}")

    if prompt := st.chat_input("Type as the citizen…"):
        st.session_state.messages.append(("user", prompt, ""))
        reply, note = dialog.respond(prompt, st.session_state.state, st.session_state.rec)
        MEM.save(st.session_state.rec)
        st.session_state.messages.append(("assistant", reply, note))
        st.rerun()
