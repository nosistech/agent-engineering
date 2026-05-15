# MIT License, Copyright 2025 Packt

import json
import os
import time


def load_env():
    """Load simple KEY=VALUE settings from a local .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8-sig") as file:
            for line in file:
                if "=" in line and not line.lstrip().startswith("#"):
                    key, _, value = line.strip().partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def required_settings():
    """Validate required settings and return LiteLLM connection values."""
    names = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        print("ERROR: Missing required environment variables:", ", ".join(missing))
        raise SystemExit(1)
    print("Active model:", os.environ["MODEL_NAME"])
    return os.environ["LITELLM_BASE_URL"], os.environ["MODEL_NAME"], os.environ["LITELLM_API_KEY"]


def build_client(base_url, api_key):
    """Create an OpenAI-compatible client pointed at LiteLLM."""
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key)


def extract_claim(client, model_name, claim_text):
    """Ask the model to extract a claim into structured fields."""
    if not isinstance(claim_text, str) or not claim_text.strip():
        return {"error": "invalid_input", "original_claim": claim_text}

    from openai import APIConnectionError, APIStatusError, RateLimitError

    prompt = (
        "Return only JSON with these fields: metric, entity, period, "
        "claimed_value, unit, original_claim.\nClaim: "
    )
    delay = 2
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt + claim_text.strip()}],
                temperature=0,
            )
            raw_text = response.choices[0].message.content or ""
            start, end = raw_text.find("{"), raw_text.rfind("}") + 1
            if start < 0 or end <= start:
                return {"error": "invalid_json", "original_claim": claim_text}
            try:
                return json.loads(raw_text[start:end])
            except json.JSONDecodeError:
                return {"error": "invalid_json", "original_claim": claim_text}
        except RateLimitError:
            if attempt == 2:
                return {"error": "rate_limit", "original_claim": claim_text}
            time.sleep(delay)
            delay *= 2
        except APIConnectionError:
            return {"error": "endpoint_unreachable", "original_claim": claim_text}
        except APIStatusError:
            return {"error": "provider_error", "original_claim": claim_text}
    return {"error": "extraction_failed", "original_claim": claim_text}


def trusted_reference_data():
    """Return fictional trusted values used by the demo."""
    return [
        {"entity": "northstar bakery", "metric": "revenue", "period": "q1 2026", "value": 1250000, "unit": "usd"},
        {"entity": "harbor clinic", "metric": "patient satisfaction", "period": "april 2026", "value": 91.0, "unit": "percent"},
        {"entity": "ridgeway logistics", "metric": "delivery accuracy", "period": "march 2026", "value": 98.4, "unit": "percent"},
    ]


def find_reference(extracted_claim, references):
    """Match extracted claim fields to trusted reference fields."""
    fields = {}
    for key in ("metric", "entity", "period", "unit"):
        fields[key] = str(extracted_claim.get(key) or "").strip().lower()
    if not all(fields.values()):
        return None
    for reference in references:
        trusted = {key: str(reference[key]).lower() for key in fields}
        if trusted == fields:
            return reference
    return None


def verify_claim(extracted_claim, reference):
    """Compare extracted claim data against trusted reference data."""
    base = {"claimed_value": extracted_claim.get("claimed_value"), "trusted_value": None, "drift": None, "unit": extracted_claim.get("unit")}
    if reference is None:
        return {**base, "verdict": "REVIEW", "reason": "No matching trusted reference was found."}
    try:
        claimed_value = float(str(extracted_claim.get("claimed_value")).replace(",", "").strip())
    except (TypeError, ValueError):
        return {**base, "verdict": "REVIEW", "reason": "The claimed value was not numeric.", "trusted_value": reference["value"], "unit": reference["unit"]}

    drift = abs(claimed_value - reference["value"])
    unit = reference["unit"]
    pass_limit, review_limit = {"usd": (5000, 50000), "percent": (0.5, 2.0)}.get(unit, (0, 0))
    verdict = "PASS" if drift <= pass_limit else "REVIEW" if drift <= review_limit else "FAIL"
    return {"verdict": verdict, "reason": "Compared against trusted reference data.", "claimed_value": claimed_value, "trusted_value": reference["value"], "drift": round(drift, 4), "unit": unit}


def run_demo(client, model_name):
    """Run three fictional claims through the verification gate."""
    claims = [
        "Northstar Bakery revenue was 1250000 USD in Q1 2026.",
        "Harbor Clinic patient satisfaction was 89.7 percent in April 2026.",
        "Ridgeway Logistics delivery accuracy was 91 percent in March 2026.",
    ]
    references = trusted_reference_data()
    for claim in claims:
        print("\nCLAIM:", claim)
        extracted = extract_claim(client, model_name, claim)
        if "error" in extracted:
            messages = {
                "endpoint_unreachable": "LiteLLM endpoint is unreachable. Confirm the proxy and base URL.",
                "rate_limit": "Provider rate limit persisted after retries.",
                "provider_error": "The provider returned an API error.",
            }
            print("VERDICT: REVIEW")
            print("REASON :", messages.get(extracted["error"], "Claim extraction failed. Manual review required."))
            continue
        result = verify_claim(extracted, find_reference(extracted, references))
        print("VERDICT      :", result["verdict"])
        print("REASON       :", result["reason"])
        print("CLAIMED VALUE:", result["claimed_value"], result["unit"])
        print("TRUSTED VALUE:", result["trusted_value"], result["unit"])
        print("DRIFT        :", result["drift"])


def main():
    """Load settings, create the client, and run the demo."""
    load_env()
    base_url, model_name, api_key = required_settings()
    run_demo(build_client(base_url, api_key), model_name)


if __name__ == "__main__":
    main()
