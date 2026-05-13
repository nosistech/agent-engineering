# MIT License, Copyright 2025 Packt

import csv
import json
import os
import statistics
import sys
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent


def load_env() -> None:
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def require_env() -> None:
    needed = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "DATA_FILE_PATH"]
    missing = [key for key in needed if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_DIR / path


def load_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def numeric_column(rows: list[dict[str, str]], column: str) -> list[tuple[int, float]]:
    values = []
    for index, row in enumerate(rows, start=1):
        try:
            values.append((index, float(row[column])))
        except (KeyError, TypeError, ValueError):
            pass
    if not values:
        raise SystemExit(f"No numeric values found for column: {column}")
    return values


def detect_anomalies(rows: list[dict[str, str]], column: str, threshold: float) -> list[dict]:
    values = numeric_column(rows, column)
    numbers = [value for _, value in values]
    mean = statistics.mean(numbers)
    stdev = statistics.pstdev(numbers)
    if stdev == 0:
        return []

    anomalies = []
    for row_number, value in values:
        z_score = (value - mean) / stdev
        if abs(z_score) >= threshold:
            anomalies.append({"row": row_number, "value": value, "z_score": round(z_score, 2)})
    return anomalies


def regression(rows: list[dict[str, str]], x_column: str, y_column: str) -> dict:
    pairs = []
    for row in rows:
        try:
            pairs.append((float(row[x_column]), float(row[y_column])))
        except (KeyError, TypeError, ValueError):
            pass
    if len(pairs) < 2:
        raise SystemExit("Regression needs at least two numeric rows.")

    xs, ys = zip(*pairs)
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(ys)
    x_var = sum((x - x_mean) ** 2 for x in xs)
    if x_var == 0:
        raise SystemExit(f"Column has no variance: {x_column}")

    slope = sum((x - x_mean) * (y - y_mean) for x, y in pairs) / x_var
    intercept = y_mean - slope * x_mean
    predictions = [intercept + slope * x for x in xs]
    total_error = sum((y - y_mean) ** 2 for y in ys)
    residual_error = sum((y - pred) ** 2 for y, pred in zip(ys, predictions))
    r_squared = 1 - residual_error / total_error if total_error else 0.0

    return {
        "x_column": x_column,
        "y_column": y_column,
        "slope": round(slope, 4),
        "r_squared": round(r_squared, 4),
    }


def call_llm(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
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


def explain(question: str, findings: dict) -> str:
    prompt = (
        "You are a business analyst. Python already computed the statistics below. "
        "Do not invent additional math. Explain the findings in plain English with "
        "three short sections: Insight, Confidence, Next Steps.\n\n"
        f"Business question: {question}\n"
        f"Computed findings:\n{json.dumps(findings, indent=2)}"
    )
    return call_llm(prompt)


def main() -> None:
    load_env()
    require_env()

    rows = load_rows(project_path(os.getenv("DATA_FILE_PATH")))
    anomaly_column = os.getenv("ANOMALY_COLUMN", "revenue")
    x_column = os.getenv("REGRESSION_X_COLUMN", "marketing_spend")
    y_column = os.getenv("REGRESSION_Y_COLUMN", "revenue")
    threshold = float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0"))
    question = os.getenv(
        "BUSINESS_QUESTION",
        "How does marketing spend relate to revenue, and are there unusual revenue days?",
    )

    findings = {
        "row_count": len(rows),
        "anomaly_column": anomaly_column,
        "anomalies": detect_anomalies(rows, anomaly_column, threshold),
        "regression": regression(rows, x_column, y_column),
    }

    print("STATISTICAL FINDINGS")
    print(json.dumps(findings, indent=2))
    print("\nANALYSIS RESULT")
    print(explain(question, findings))


if __name__ == "__main__":
    main()
