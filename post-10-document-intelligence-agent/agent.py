# MIT License, Copyright 2025 Packt
import json
import os
import re
import sys
import time
from pathlib import Path

import pytesseract
from dotenv import load_dotenv
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError

load_dotenv()

def _require_env(var_name: str) -> str:
    """Return value of required environment variable or exit with a clear message."""
    value = os.getenv(var_name)
    if value is None:
        sys.exit(
            f"Missing required environment variable: {var_name}. "
            "Please set it in your .env file or environment."
        )
    return value

def load_document(path: str) -> Image.Image:
    """Load a document (PNG, JPG, PDF) and return a PIL image of its first page, exiting cleanly on failure."""
    file_path = Path(path)
    if not file_path.exists():
        sys.exit(f"Document not found: {file_path.name}")
    suffix = file_path.suffix.lower()
    if suffix in ('.png', '.jpg', '.jpeg'):
        try:
            image = Image.open(file_path)
            image.load()
            return image
        except (UnidentifiedImageError, OSError) as exc:
            sys.exit(f"Unable to open image {file_path.name}: {exc}")
    elif suffix == '.pdf':
        try:
            pages = convert_from_path(file_path, first_page=1, last_page=1)
        except Exception as exc:
            sys.exit(f"Could not convert PDF {file_path.name} to image: {exc}")
        if not pages:
            sys.exit(f"PDF {file_path.name} contains no pages.")
        return pages[0]
    else:
        sys.exit(f"Unsupported file type: {suffix}. Supported types: .png, .jpg, .jpeg, .pdf")

def run_ocr(image: Image.Image):
    """Run OCR on the image and return (raw_text, mean_confidence_float)."""
    tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [int(c) for c in data['conf'] if c != '-1']
    if not confidences:
        mean_conf = 0.0
    else:
        mean_conf = sum(confidences) / len(confidences)
    raw_text = pytesseract.image_to_string(image)
    return raw_text, mean_conf

def _get_model_client():
    """Create and return an OpenAI client pointed at the LiteLLM proxy."""
    try:
        client = OpenAI(
            base_url=os.getenv("LITELLM_BASE_URL"),
            api_key=os.getenv("LITELLM_API_KEY"),
        )
        return client
    except Exception as exc:
        sys.exit(f"Could not initialise AI model client: {exc}")

def _call_litellm(system_prompt: str, user_message: str, max_retries=3) -> str:
    """Call LiteLLM proxy via OpenAI SDK with retries on rate limits, returning the model's text response."""
    client = _get_model_client()
    model = os.getenv("MODEL_NAME")
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as exc:
            error_str = str(exc).lower()
            if "rate limit" in error_str:
                wait = 2 ** attempt
                print(f"Rate limited. Retrying in {wait}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait)
                if attempt == max_retries:
                    sys.exit("AI model request failed after multiple rate limit retries.")
            else:
                sys.exit(f"AI model request failed: {exc}")

def correction_pass(raw_text: str) -> str:
    """Attempt to correct common OCR misreads using the LLM."""
    system_prompt = (
        "You are a document correction assistant. The following text was extracted by OCR "
        "and may contain character substitution errors. Common errors include letters replacing numbers "
        "such as S for 5, O for 0, I for 1, and B for 8. Return only the corrected text with no explanation."
    )
    corrected = _call_litellm(system_prompt, raw_text)
    return corrected.strip()

def extract_fields(text: str) -> str:
    """Extract specified fields from text and return the raw LLM response string."""
    fields_raw = os.getenv("EXTRACTION_FIELDS")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()]
    fields_list = ", ".join(fields)
    system_prompt = (
        f"You are a data extraction assistant. Extract the following fields from the document text "
        f"and return only a valid JSON object with no markdown formatting and no explanation. "
        f"Fields: {fields_list}. If a field cannot be found, return null for that key."
    )
    return _call_litellm(system_prompt, text)

def parse_llm_response(response_text: str) -> dict:
    """Strip markdown fences and parse JSON, exiting with a clear message on failure."""
    cleaned = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        sys.exit(
            "Failed to parse the AI model response. "
            "It did not return valid JSON. Raw output:\n" + cleaned[:200]
        )

def apply_confidence_gate(extracted_data: dict, ocr_confidence: float, threshold: float):
    """Return (accepted, data) if confidence >= threshold, else (flagged, data)."""
    if ocr_confidence >= threshold:
        return "accepted", extracted_data
    return "flagged", extracted_data

def write_output(status: str, ocr_confidence: float, source_path: str, extracted_data: dict = None):
    """Persist extracted data to output file if accepted, or append to human review queue if flagged."""
    doc_name = Path(source_path).name
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    if status == "accepted":
        output_path = os.getenv("OUTPUT_PATH")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        field_count = len(extracted_data)
        print(f"Extraction successful. {field_count} fields written to output. OCR confidence: {ocr_confidence:.1f}%")
    else:
        review_path = os.getenv("REVIEW_QUEUE_PATH")
        Path(review_path).parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "filename": doc_name,
            "timestamp": timestamp,
            "ocr_confidence": round(ocr_confidence, 1),
            "human_review_required": True
        }
        with open(review_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"Document routed for human review. OCR confidence: {ocr_confidence:.1f}%")

def main():
    """Run the document intelligence extraction pipeline."""
    required_vars = [
        "LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY",
        "CONFIDENCE_THRESHOLD", "LOW_CONFIDENCE_FLOOR",
        "INPUT_DOCUMENT_PATH", "OUTPUT_PATH", "REVIEW_QUEUE_PATH",
        "EXTRACTION_FIELDS"
    ]
    missing = [v for v in required_vars if os.getenv(v) is None]
    if missing:
        sys.exit(
            "Missing required environment variable(s): " + ", ".join(missing) +
            ". Please set them in your .env file or environment."
        )
    model_name = os.getenv("MODEL_NAME")
    print(f"Active AI model: {model_name}")
    input_path = os.getenv("INPUT_DOCUMENT_PATH")
    print(f"Processing document: {Path(input_path).name}")
    image = load_document(input_path)
    raw_text, ocr_conf = run_ocr(image)
    print(f"OCR confidence: {ocr_conf:.1f}%")
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD"))
    floor = float(os.getenv("LOW_CONFIDENCE_FLOOR"))
    if ocr_conf < floor:
        print("Confidence is below the correction floor. Skipping extraction and routing for review.")
        write_output(status="flagged", ocr_confidence=ocr_conf, source_path=input_path)
        sys.exit(0)
    extraction_text = raw_text
    if floor <= ocr_conf < threshold:
        print("Confidence is below threshold. Attempting AI correction pass...")
        try:
            corrected = correction_pass(raw_text)
            extraction_text = corrected
            print("Correction pass completed.")
        except SystemExit:
            raise
        except Exception as exc:
            sys.exit(f"Correction pass failed: {exc}")
    try:
        llm_response = extract_fields(extraction_text)
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"Field extraction failed: {exc}")
    extracted_data = parse_llm_response(llm_response)
    status, _ = apply_confidence_gate(extracted_data, ocr_conf, threshold)
    write_output(status, ocr_confidence=ocr_conf, source_path=input_path, extracted_data=extracted_data)

if __name__ == "__main__":
    main()