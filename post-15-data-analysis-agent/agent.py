# MIT License, Copyright 2025 Packt

import csv
import json
import os
import statistics
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "DATA_FILE_PATH")


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def read_csv(path):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def anomalies(rows, column, threshold):
    values = []
    for row_number, row in enumerate(rows, start=1):
        try:
            values.append((row_number, float(row[column])))
        except (KeyError, TypeError, ValueError):
            pass

    if not values:
        raise SystemExit(f"No numeric values found for column: {column}")

    numbers = [value for _, value in values]
    stdev = statistics.pstdev(numbers)
    if stdev == 0:
        return []

    mean = statistics.mean(numbers)
    return [
        {"row": row, "value": value, "z_score": round((value - mean) / stdev, 2)}
        for row, value in values
        if abs((value - mean) / stdev) >= threshold
    ]


def regression(rows, x_column, y_column):
    pairs = []
    for row in rows:
        try:
            pairs.append((float(row[x_column]), float(row[y_column])))
        except (KeyError, TypeError, ValueError):
            pass
    if len(pairs) < 2:
        raise SystemExit("The CSV needs at least two numeric rows for regression.")

    xs, ys = zip(*pairs)
    slope, _ = statistics.linear_regression(xs, ys)
    r_squared = statistics.correlation(xs, ys) ** 2
    return {
        "x_column": x_column,
        "y_column": y_column,
        "slope": round(slope, 4),
        "r_squared": round(r_squared, 4),
    }


def ask_model(question, findings):
    prompt = (
        "You are a business analyst. Python already computed these statistics. "
        "Do not invent more math, probabilities, or extra metrics. Explain the "
        "findings with three short sections: Insight, Confidence, Next Steps.\n\n"
        f"Business question: {question}\n"
        f"Computed findings:\n{json.dumps(findings, indent=2)}"
    )
    body = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode("utf-8")

    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()

    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    rows = read_csv(os.getenv("DATA_FILE_PATH"))
    anomaly_column = os.getenv("ANOMALY_COLUMN", "revenue")
    findings = {
        "row_count": len(rows),
        "anomaly_column": anomaly_column,
        "anomalies": anomalies(
            rows,
            anomaly_column,
            float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0")),
        ),
        "regression": regression(
            rows,
            os.getenv("REGRESSION_X_COLUMN", "marketing_spend"),
            os.getenv("REGRESSION_Y_COLUMN", "revenue"),
        ),
    }
    question = os.getenv(
        "BUSINESS_QUESTION",
        "How does marketing spend relate to revenue, and are there unusual revenue days?",
    )

    print("STATISTICAL FINDINGS")
    print(json.dumps(findings, indent=2))
    print("\nANALYSIS RESULT")
    print(ask_model(question, findings))


if __name__ == "__main__":
    main()
