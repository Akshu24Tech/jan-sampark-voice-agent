"""List the Groq chat models your API key can actually use.

Groq rotates model availability and it differs by account, so a model that
works for one key 404s for another. Run this to see valid LLM_MODEL values:

    uv run python -m jan_sampark_voice_agent.list_models
"""
from __future__ import annotations

import os
import urllib.request
import json

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(".env.local")
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("GROQ_API_KEY not set (check .env.local)")
        return
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    skip = ("whisper", "tts", "guard", "orpheus")  # audio / safety models
    ids = sorted(m["id"] for m in data.get("data", []))
    chat = [i for i in ids if not any(s in i.lower() for s in skip)]
    print("Chat models available to this key (use one as JS_LLM_MODEL):")
    for i in chat:
        print(f"  {i}")


if __name__ == "__main__":
    main()
