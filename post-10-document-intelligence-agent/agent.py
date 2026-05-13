# MIT License, Copyright 2025 Packt

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pytesseract
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parent
FIELDS = ["invoice_number", "invoice_date", "total_amount"]


def load_env() -> None:
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def require_env() -> None:
    needed = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "CONFIDENCE_THRESHOLD",
        "INPUT_DOCUMENT_PATH",
        "OUTPUT_PATH",
        "REVIEW_QUEUE_PATH",
    ]
    missing = [key for key in needed if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_DIR / path


def run_ocr(image_path: Path) -> tuple[str, float]:
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")
    image = Image.open(image_path)
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    scores = [int(score) for score in ocr_data["conf"] if score != "-1"]
    confidence = sum(scores) / len(scores) if scores else 0.0
    return pytesseract.image_to_string(image), confidence


def call_llm(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode("utf-8")

    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def extract_fields(text: str) -> dict:
    prompt = (
        "Extract invoice fields from the OCR text. "
        f"Return only JSON with these keys: {', '.join(FIELDS)}. "
        "Use null when a value is missing.\n\n"
        f"OCR text:\n{text}"
    )
    raw = call_llm(prompt)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)


def write_accepted(data: dict, confidence: float) -> None:
    output_path = project_path(os.getenv("OUTPUT_PATH"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ocr_confidence": round(confidence, 1), "fields": data}
    output_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"[ACCEPTED] Wrote extracted fields to {output_path}")


def write_review(image_path: Path, confidence: float, raw_text: str) -> None:
    review_path = project_path(os.getenv("REVIEW_QUEUE_PATH"))
    review_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document": image_path.name,
        "ocr_confidence": round(confidence, 1),
        "raw_text_preview": raw_text[:300],
        "human_review_required": True,
    }
    with open(review_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
    print(f"[REVIEW] Routed {image_path.name} to human review")


def main() -> None:
    load_env()
    require_env()

    image_path = project_path(os.getenv("INPUT_DOCUMENT_PATH"))
    if not image_path.exists():
        raise SystemExit(f"Document not found: {image_path}")

    raw_text, confidence = run_ocr(image_path)
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD"))
    print(f"[OCR] {image_path.name} confidence: {confidence:.1f}%")

    if confidence < threshold:
        write_review(image_path, confidence, raw_text)
        return

    extracted = extract_fields(raw_text)
    write_accepted(extracted, confidence)


if __name__ == "__main__":
    main()
