# (c) 2026 NosisTech LLC. Original implementation.
# Calls a Langflow RFP Analyzer flow through its REST API.

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
REQUIRED_ENV = ("LANGFLOW_API_KEY", "LANGFLOW_FLOW_ID")
SAMPLE_RFP = (
    "NosisTech LLC is seeking a vendor to build an AI governance dashboard. "
    "The project must be completed by September 30, 2026. "
    "The vendor must comply with EU AI Act Article 13 transparency requirements. "
    "Estimated budget is between $50,000 and $80,000 USD."
)


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def analyze_rfp(text):
    base_url = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860").rstrip("/")
    url = f"{base_url}/api/v1/run/{os.getenv('LANGFLOW_FLOW_ID')}"
    body = json.dumps(
        {
            "output_type": "chat",
            "input_type": "chat",
            "input_value": text,
            "session_id": str(uuid.uuid4()),
            "tweaks": {
                "OpenAIModel-y92rB": {
                    "model_name": os.getenv("LANGFLOW_MODEL_NAME", "deepseek-v4-pro"),
                    "openai_api_base": os.getenv("LANGFLOW_OPENAI_API_BASE", "http://localhost:4000"),
                }
            },
        }
    ).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.getenv("LANGFLOW_API_KEY"),
        },
    )

    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(
            f"Langflow returned HTTP {error.code}: {error.reason}\n{details}"
        ) from error
    except URLError as error:
        raise SystemExit(f"Could not connect to Langflow at {base_url}: {error}") from error
    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unexpected Langflow response format: {error}") from error


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()
    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    print("RFP INPUT")
    print(SAMPLE_RFP)
    print("\nANALYSIS")
    print(analyze_rfp(SAMPLE_RFP))


if __name__ == "__main__":
    main()
