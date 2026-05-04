import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

def update_elevenlabs_workflow():
    """
    Updates the ElevenLabs agent with the full Sarah Master Prompt,
    dynamic logic, and analysis schema via API.
    """
    if not AGENT_ID or not API_KEY:
        print("Error: ELEVENLABS_AGENT_ID or ELEVENLABS_API_KEY missing.")
        return

    url = f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    # Load the master prompt from the local file
    try:
        with open("sarah_master_prompt.md", "r") as f:
            full_prompt = f.read()
    except FileNotFoundError:
        print("Error: sarah_master_prompt.md not found.")
        return

    # Payload for Agent Workflow and Configuration
    payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": full_prompt
                },
                "first_message": "Hi, is this {{first_name}}? This is Sarah with Roof Hunter Pro.",
                "language": "en",
                "use_enhanced_speech_detection": True
            },
            "asr": {
                "quality": "high"
            },
            "turn": {
                "turn_timeout_ms": 700
            }
        },
        "platform_settings": {
            "post_call_analysis_config": {
                "summary_prompt": "Summarize the conversation focusing on whether an inspection was booked and the specific damage concerns the homeowner had.",
                "success_evaluation_prompt": "Was a roof inspection successfully booked or scheduled? Respond with true or false.",
                "transcript_export_format": "json"
            }
        }
    }

    print(f"Updating ElevenLabs Agent {AGENT_ID}...")
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("✅ Workflow successfully updated.")
        print(f"Agent Name: {response.json().get('name')}")
    else:
        print(f"❌ Update failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    update_elevenlabs_workflow()
