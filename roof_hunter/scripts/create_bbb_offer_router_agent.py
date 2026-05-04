#!/usr/bin/env python3
"""
Create a new ElevenLabs ConvAI agent: "BBB Offer Router".

Requires:
  export ELEVENLABS_API_KEY=xi-...

Optional:
  export ELEVENLABS_AGENT_VOICE_ID=<voice_id>   (default: ElevenLabs default voice id below)
  export ELEVENLABS_BBB_TTS_MODEL=eleven_turbo_v2   # English agents: turbo or flash v2

Usage:
  python3 scripts/create_bbb_offer_router_agent.py
  python3 scripts/create_bbb_offer_router_agent.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

CREATE_URL = "https://api.elevenlabs.io/v1/convai/agents/create"
REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = REPO_ROOT / "prompts" / "bbb_offer_router_elevenlabs.md"


def load_prompt() -> str:
    if not PROMPT_PATH.is_file():
        print(f"Missing prompt file: {PROMPT_PATH}", file=sys.stderr)
        sys.exit(1)
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_payload() -> dict:
    prompt = load_prompt()
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_AGENT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    llm = os.getenv("ELEVENLABS_BBB_AGENT_LLM", "gpt-4o-mini")
    tts_model = os.getenv("ELEVENLABS_BBB_TTS_MODEL", "eleven_turbo_v2")

    first_message = (
        "Hey — is this {{company}}? Perfect. I'll be quick. "
        "I'm calling because we help businesses like yours with {{reason_for_fit}}."
    )

    return {
        "name": "BBB Offer Router",
        "tags": [
            "bbb",
            "better-business-builder",
            "sales-router",
            "multi-offer",
        ],
        "conversation_config": {
            "asr": {"quality": "high"},
            "turn": {"turn_timeout_ms": 750},
            "tts": {
                "model_id": tts_model,
                "voice_id": voice_id,
            },
            "agent": {
                "first_message": first_message,
                "language": "en",
                "use_enhanced_speech_detection": True,
                "prompt": {
                    "prompt": prompt,
                    "llm": llm,
                    "temperature": 0.65,
                },
            },
        },
        "platform_settings": {
            "post_call_analysis_config": {
                "summary_prompt": (
                    "Produce structured JSON ONLY (no markdown) with exactly these keys: "
                    "lead_status (one of: hot, warm, cold, bad_fit, no_answer, callback, do_not_call), "
                    "offer_used (string: Roof Hunter Pro | ChatterTech.ai | Flowstate.work | QuLabInfinite | unknown), "
                    "pain_points (JSON array of short strings), "
                    "objections (JSON array of short strings), "
                    "next_step (string), "
                    "callback_time (string, empty if none), "
                    "decision_maker (string), "
                    "notes (string)."
                ),
                "success_evaluation_prompt": (
                    "true if the contact agreed to any positive next step: demo, scheduled callback, "
                    "quote review, pilot, transfer to owner, or explicit permission to send text/email info. "
                    "Otherwise false."
                ),
                "transcript_export_format": "json",
            }
        },
        "_env_check": bool(api_key),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print payload only; do not call API")
    args = parser.parse_args()

    payload = build_payload()
    payload.pop("_env_check", None)

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if args.dry_run:
        print(json.dumps({k: v for k, v in payload.items() if k != "conversation_config"}, indent=2))
        print(
            "\n[conversation_config.agent.prompt length:",
            len(payload["conversation_config"]["agent"]["prompt"]["prompt"]),
            "chars]\n",
        )
        return

    if not api_key:
        print("Set ELEVENLABS_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)

    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    r = requests.post(CREATE_URL, headers=headers, json=payload, timeout=120)
    if r.status_code == 422 and "platform_settings" in payload:
        print("Note: Retrying without platform_settings (add analysis in ElevenLabs UI if needed).", file=sys.stderr)
        retry = {k: v for k, v in payload.items() if k != "platform_settings"}
        r = requests.post(CREATE_URL, headers=headers, json=retry, timeout=120)
        payload = retry
    if r.status_code not in (200, 201):
        print(f"Create failed HTTP {r.status_code}:\n{r.text}", file=sys.stderr)
        sys.exit(1)

    data = r.json()
    agent_id = data.get("agent_id") or data.get("id")
    print("Created ElevenLabs ConvAI agent.")
    print(f"   agent_id: {agent_id}")
    print(f"   name: {data.get('name', payload['name'])}")
    print("\nNext steps:")
    print("  1. ElevenLabs dashboard: Conversational AI -> open agent -> phone / SIP / widget.")
    print("  2. Outbound: pass dynamic variables (lead_name, company, reason_for_fit, ...).")
    print(f"  3. Optional env: ELEVENLABS_BBB_AGENT_ID={agent_id}")
    print(f"\nPrompt source file: {PROMPT_PATH}")


if __name__ == "__main__":
    main()
