# (c) 2026 NosisTech LLC. Original implementation.
# Calls the Langflow RFP Analyzer flow via its auto-generated REST API.
# Requires Langflow Desktop running locally and a Langflow API key.
# All configuration via .env file. Never hardcode credentials.

import requests
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY")
LANGFLOW_FLOW_ID = os.getenv("LANGFLOW_FLOW_ID")
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")


def check_env() -> None:
    """Verify required environment variables are present before making any API call."""
    missing = []
    if not LANGFLOW_API_KEY:
        missing.append("LANGFLOW_API_KEY")
    if not LANGFLOW_FLOW_ID:
        missing.append("LANGFLOW_FLOW_ID")
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.template to .env and fill in your values.")
        raise SystemExit(1)


def analyze_rfp(user_input: str) -> str:
    """Send RFP text to the Langflow flow and return the structured analysis."""
    url = f"{LANGFLOW_BASE_URL}/api/v1/run/{LANGFLOW_FLOW_ID}"

    payload = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": user_input,
        "session_id": str(uuid.uuid4()),
    }

    headers = {"x-api-key": LANGFLOW_API_KEY}

    print(f"Sending request to Langflow flow: {LANGFLOW_FLOW_ID}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        result = data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        return result
    except requests.exceptions.ConnectionError:
        print("Could not connect to Langflow. Make sure Langflow Desktop is running.")
        raise SystemExit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Langflow returned an error: {e}")
        raise SystemExit(1)
    except (KeyError, IndexError):
        print("Unexpected response format from Langflow.")
        print("Raw response:", response.text[:500])
        raise SystemExit(1)


if __name__ == "__main__":
    check_env()

    sample_rfp = (
        "NosisTech LLC is seeking a vendor to build an AI governance dashboard. "
        "The project must be completed by September 30, 2026. "
        "The vendor must comply with EU AI Act Article 13 transparency requirements. "
        "Estimated budget is between $50,000 and $80,000 USD."
    )

    print("\nRFP Input:")
    print(sample_rfp)
    print("\nAnalysis:")
    result = analyze_rfp(sample_rfp)
    print(result)
