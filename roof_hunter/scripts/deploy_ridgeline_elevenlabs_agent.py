#!/usr/bin/env python3
"""
Create or update an ElevenLabs Conversational AI agent for Ridgeline.ai / Roof Hunter Pro:
B2B sales to roofing contractors (subscriptions, leads, territory).

Requires:
  ELEVENLABS_API_KEY in .env

Env (optional):
  RIDGELINE_TRANSFER_E164   default +17252241240
  RIDGELINE_ELEVENLABS_AGENT_ID   used for --update (defaults to production roof hunter sales agent)

Production agent (dashboard): roof hunter sales agent → agent_9601kq1b8dxkeh6snk5cjf4wb70h
Web dashboard embed: VITE_ELEVENLABS_SALES_AGENT_ID (optional; same default in SalesAgentWidget.jsx)

Usage:
  python scripts/deploy_ridgeline_elevenlabs_agent.py --create
  python scripts/deploy_ridgeline_elevenlabs_agent.py --update
  python scripts/deploy_ridgeline_elevenlabs_agent.py --update --prompt prompts/ridgeline_ok_tx_territory_sales_elevenlabs.md

Optional: RIDGELINE_B2B_FIRST_MESSAGE overrides the auto-picked opening line.
"""

from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "ridgeline_lead_sales_elevenlabs.md")
OK_TX_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "ridgeline_ok_tx_territory_sales_elevenlabs.md")

DEFAULT_FIRST_MESSAGE = (
    "Hey {{contact_name}} — quick call from Ridgeline A I. "
    "We help roofers in {{metro_area}} spot hail-related roof damage faster "
    "using HD satellite imagery — is now an okay time for a thirty-second pitch?"
)

OK_TX_FIRST_MESSAGE = (
    "Hey {{contact_name}} — {{agent_name}} with Ridgeline A I. "
    "We're speaking with Oklahoma and Texas roofers today about verified storm-market "
    "lead packages and optional exclusive territories—got forty-five seconds?"
)

CREATE_URL = "https://api.elevenlabs.io/v1/convai/agents/create"

# Dashboard name: "roof hunter sales agent" (ElevenLabs UI)
DEFAULT_ROOF_HUNTER_SALES_AGENT_ID = "agent_9601kq1b8dxkeh6snk5cjf4wb70h"


def _transfer_tool(phone_e164: str) -> dict:
    return {
        "name": "transfer_to_number",
        "description": (
            "When the roofing company contact asks to speak with a human right now, "
            "confirms they want an immediate connection, or says yes to being transferred "
            "to the owner, invoke this tool to connect them."
        ),
        "params": {
            "system_tool_type": "transfer_to_number",
            "enable_client_message": True,
            "transfers": [
                {
                    "condition": (
                        "Prospect explicitly wants to speak with someone immediately "
                        "or confirms a live transfer to the owner/partner."
                    ),
                    "transfer_destination": {
                        "type": "phone",
                        "phone_number": phone_e164,
                    },
                    "transfer_type": "conference",
                }
            ],
        },
    }


def _conversation_config(prompt_text: str, phone_e164: str, *, first_message: str) -> dict:
    return {
        "asr": {"quality": "high"},
        "turn": {"turn_timeout_ms": 750},
        "agent": {
            "first_message": first_message,
            "language": "en",
            "disable_first_message_interruptions": False,
            "prompt": {
                "prompt": prompt_text,
                "temperature": 0.35,
                "built_in_tools": {
                    "transfer_to_number": _transfer_tool(phone_e164),
                    "end_call": {
                        "name": "end_call",
                        "params": {"system_tool_type": "end_call"},
                    },
                },
            },
        },
    }


def _platform_settings() -> dict:
    return {
        "post_call_analysis_config": {
            "summary_prompt": (
                "Summarize this B2B call for Ridgeline.ai. Include: company name, "
                "contact name and role, interest level (subscription, individual leads, "
                "or exclusive territory), markets mentioned, objections, best callback "
                "number and email, whether live transfer was attempted or completed, "
                "and recommended next step."
            ),
            "success_evaluation_prompt": (
                "Did the prospect show buying interest (callback, transfer, or clear "
                "request for follow-up)? Answer true or false."
            ),
            "transcript_export_format": "json",
        }
    }


def _first_message_for_prompt(prompt_path: str) -> str:
    env_fm = os.getenv("RIDGELINE_B2B_FIRST_MESSAGE")
    if env_fm and env_fm.strip():
        return env_fm.strip()
    resolved = os.path.abspath(prompt_path)
    if resolved == os.path.abspath(OK_TX_PROMPT_PATH) or "ok_tx_territory" in os.path.basename(
        prompt_path
    ):
        return OK_TX_FIRST_MESSAGE
    return DEFAULT_FIRST_MESSAGE


def create_agent(api_key: str, phone_e164: str, prompt_path: str) -> str:
    with open(prompt_path, encoding="utf-8") as f:
        prompt_text = f.read()
    # Inject visible placeholder so dashboard dynamic vars match prompt wording
    prompt_text = prompt_text.replace("{{owner_transfer_e164}}", phone_e164)
    first_message = _first_message_for_prompt(prompt_path)

    payload = {
        "name": "Ridgeline.ai — Roofing lead sales",
        "tags": ["ridgeline", "roofing", "b2b", "leads"],
        "conversation_config": _conversation_config(prompt_text, phone_e164, first_message=first_message),
        "platform_settings": _platform_settings(),
    }
    r = requests.post(
        CREATE_URL,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if r.status_code != 200:
        print(f"Create failed {r.status_code}: {r.text}", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    agent_id = data.get("agent_id")
    if not agent_id:
        print(data, file=sys.stderr)
        sys.exit(1)
    return agent_id


def update_agent(api_key: str, agent_id: str, phone_e164: str, prompt_path: str) -> None:
    with open(prompt_path, encoding="utf-8") as f:
        prompt_text = f.read()
    prompt_text = prompt_text.replace("{{owner_transfer_e164}}", phone_e164)
    first_message = _first_message_for_prompt(prompt_path)

    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    payload = {
        "conversation_config": _conversation_config(
            prompt_text, phone_e164, first_message=first_message
        ),
        "platform_settings": _platform_settings(),
    }
    r = requests.patch(
        url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if r.status_code != 200:
        print(f"Update failed {r.status_code}: {r.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Deploy Ridgeline.ai ElevenLabs agent")
    ap.add_argument("--create", action="store_true", help="POST new agent")
    ap.add_argument("--update", action="store_true", help="PATCH existing agent id from env")
    ap.add_argument(
        "--prompt",
        metavar="PATH",
        default=DEFAULT_PROMPT_PATH,
        help=f"System prompt markdown (default: ridgeline_lead_sales). OK/TX: {OK_TX_PROMPT_PATH}",
    )
    args = ap.parse_args()
    if args.create == args.update:
        print("Specify exactly one of --create or --update", file=sys.stderr)
        sys.exit(2)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY missing in environment.", file=sys.stderr)
        sys.exit(1)

    phone = os.getenv("RIDGELINE_TRANSFER_E164", "+17252241240").strip()
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("+")

    prompt_path = os.path.abspath(args.prompt)
    if not os.path.isfile(prompt_path):
        print(f"Prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)

    if args.create:
        aid = create_agent(api_key, phone, prompt_path)
        print(f"Created agent_id={aid}")
        print(f"Add to .env: RIDGELINE_ELEVENLABS_AGENT_ID={aid}")
        print(
            "\nNext: In ElevenLabs dashboard, enable phone/SIP outbound if needed, "
            "define dynamic variables (contact_name, metro_area, company_name, agent_name). "
            "Optional: add a webhook/SMS tool to text lead summaries to your cell when "
            "transfer does not connect.\n"
            f"Production sales agent id (if this IS that agent): {DEFAULT_ROOF_HUNTER_SALES_AGENT_ID}"
        )
    else:
        aid = os.getenv("RIDGELINE_ELEVENLABS_AGENT_ID") or DEFAULT_ROOF_HUNTER_SALES_AGENT_ID
        if not os.getenv("RIDGELINE_ELEVENLABS_AGENT_ID"):
            print(
                f"No RIDGELINE_ELEVENLABS_AGENT_ID — updating default roof hunter sales agent ({aid}).",
                file=sys.stderr,
            )
        update_agent(api_key, aid, phone, prompt_path)
        print(f"Updated agent {aid}")


if __name__ == "__main__":
    main()
