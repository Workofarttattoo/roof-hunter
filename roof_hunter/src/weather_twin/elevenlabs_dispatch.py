import os
import requests
import json
from datetime import datetime
from typing import Dict, Any

class ElevenLabsDispatch:
    """
    Automated Voice Dispatch via ElevenLabs.
    Triggers when the 70% 'Beat ZWeather' threshold is hit.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = "21m00Tcm4lP38O2W8PaA" # Default 'Rachel' voice or similar
        self.base_url = "https://api.elevenlabs.io/v1"

    def trigger_hail_alert(self, storm_data: Dict[str, Any]):
        """Generates a voice alert for the sales team."""
        if not self.api_key:
            print("[ELEVENLABS] Error: API Key not set.")
            return

        county = storm_data.get('county', 'Unknown Region')
        prob = storm_data.get('hail_probability', 0.7)
        lead_time = storm_data.get('lead_time_min', 240)
        target_count = storm_data.get('target_count', 100)

        message = (
            f"Attention Roof Hunter Sales Team. High-priority hail risk detected for {county} County. "
            f"Our models show a {prob:.0%} probability of impact in {lead_time} minutes. "
            f"A target pack of {target_count} high-value roofs has been generated and is ready in your dialer. "
            f"I repeat, dispatch is authorized for {county}."
        )

        print(f"[ELEVENLABS] Generating voice alert: '{message}'")
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        data = {
            "text": message,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/text-to-speech/{self.voice_id}",
                json=data,
                headers=headers
            )
            if response.status_code == 200:
                output_path = f"monitoring/alerts/hail_alert_{datetime.now().strftime('%Y%m%d_%H%M')}.mp3"
                os.makedirs("monitoring/alerts", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"[ELEVENLABS] Alert generated successfully: {output_path}")
                return output_path
            else:
                print(f"[ELEVENLABS] Failed to generate alert: {response.text}")
        except Exception as e:
            print(f"[ELEVENLABS] Exception during dispatch: {e}")

        return None

if __name__ == "__main__":
    # Test alert
    dispatcher = ElevenLabsDispatch()
    dispatcher.trigger_hail_alert({
        "county": "Oklahoma",
        "hail_probability": 0.72,
        "lead_time_min": 240,
        "target_count": 103
    })
