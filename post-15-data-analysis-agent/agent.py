# MIT License, Copyright 2025 Packt
import os
import time
import sys
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIConnectionError, APIError
import pandas as pd
import numpy as np


def load_and_validate_csv(file_path):
    """Load a CSV file and return a DataFrame, exiting cleanly if the file is missing."""
    if not os.path.exists(file_path):
        print(f"Data file not found. Check DATA_FILE_PATH in your .env file.")
        sys.exit(1)
    return pd.read_csv(file_path)


def detect_anomalies(dataframe, column_name, threshold):
    """Compute Z-scores for a numeric column and return anomaly dictionaries for rows exceeding the threshold."""
    if column_name not in dataframe.columns:
        print(f"Column '{column_name}' not found in dataset. Exiting.")
        sys.exit(1)
    values = dataframe[column_name].dropna().astype(float)
    if len(values) == 0:
        return []
    mean_val = np.mean(values)
    std_val = np.std(values, ddof=0)
    if std_val == 0:
        return []
    z_scores = (values - mean_val) / std_val
    anomalies = []
    for idx, (orig_idx, z) in enumerate(zip(values.index, z_scores)):
        if abs(z) > threshold:
            anomalies.append({
                "row_index": orig_idx,
                "value": float(values.iloc[idx]),
                "z_score": round(float(z), 3)
            })
    return anomalies


def run_ols_regression(dataframe, x_column, y_column):
    """Perform OLS regression using numpy and return R-squared, coefficient, p-value, and confidence label."""
    if x_column not in dataframe.columns or y_column not in dataframe.columns:
        print("Regression column not found in dataset. Exiting.")
        sys.exit(1)
    clean_df = dataframe[[x_column, y_column]].dropna().astype(float)
    if clean_df.empty:
        print("No valid data points after dropping NA values. Exiting.")
        sys.exit(1)
    x = clean_df[x_column].values
    y = clean_df[y_column].values
    n = len(x)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_yy = np.sum((y - y_mean) ** 2)
    if ss_xx == 0:
        print("Independent variable has no variance. Regression not possible. Exiting.")
        sys.exit(1)
    coef = ss_xy / ss_xx
    intercept = y_mean - coef * x_mean
    y_pred = coef * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    r_squared = 1 - (ss_res / ss_yy) if ss_yy != 0 else 0.0
    # Compute p-value for coefficient using t-distribution approximation
    if n > 2 and ss_res > 0:
        se = np.sqrt((ss_res / (n - 2)) / ss_xx)
        t_stat = coef / se if se != 0 else 0.0
        # Two-tailed p-value approximation using normal distribution for large n
        # For small n this is an approximation but sufficient for business insight use
        from math import erfc, sqrt
        p_value = erfc(abs(t_stat) / sqrt(2))
    else:
        p_value = 1.0
    if p_value < 0.05:
        confidence_label = "high"
    elif p_value < 0.10:
        confidence_label = "medium"
    else:
        confidence_label = "low"
    return {
        "r_squared": round(float(r_squared), 4),
        "coefficient": round(float(coef), 4),
        "p_value": round(float(p_value), 4),
        "confidence": confidence_label
    }


def recommend_visualization(business_question):
    """Map the business question to a chart type using keyword matching, no LLM call."""
    question_lower = business_question.lower()
    if "trend" in question_lower or "over time" in question_lower:
        return "line chart"
    if "compare" in question_lower or "breakdown" in question_lower:
        return "bar chart"
    if "distribution" in question_lower or "spread" in question_lower:
        return "histogram"
    if "relationship" in question_lower or "correlation" in question_lower:
        return "scatter plot"
    return "table"


def build_analysis_prompt(business_question, anomalies, regression_results, chart_recommendation):
    """Construct the LLM prompt from statistical findings and the chart suggestion."""
    anomaly_str = "No anomalies detected." if not anomalies else "\n".join(
        f"Row {a['row_index']}: value={a['value']}, Z-score={a['z_score']}" for a in anomalies
    )
    reg_str = (
        f"R-squared={regression_results['r_squared']}, "
        f"coefficient={regression_results['coefficient']}, "
        f"p-value={regression_results['p_value']}, "
        f"confidence={regression_results['confidence']}"
    )
    prompt = (
        "You are a business intelligence analyst. Using the statistical findings below, "
        "answer the business question clearly.\n\n"
        f"Business question: {business_question}\n\n"
        "Statistical findings:\n\n"
        f"Anomalies detected (Z-score analysis):\n{anomaly_str}\n\n"
        f"Regression analysis (OLS):\n{reg_str}\n\n"
        f"Recommended visualization: {chart_recommendation}\n\n"
        "Provide your answer in the following structure:\n\n"
        "INSIGHT: [a short, plain-English paragraph explaining what the data reveals]\n"
        "CONFIDENCE: [high/medium/low] - [one sentence explaining why]\n"
        "NEXT STEPS: [two to three concrete, actionable recommendations for a decision-maker]"
    )
    return prompt


def call_llm_with_retry(client, model_name, prompt, max_attempts=3):
    """Send prompt to LiteLLM via openai SDK with exponential backoff on rate limit errors."""
    attempt = 0
    wait_time = 2
    while attempt < max_attempts:
        attempt += 1
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            if attempt == max_attempts:
                print("Rate limit exceeded after multiple attempts. Exiting.")
                sys.exit(1)
            print(f"Rate limited. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            wait_time *= 2
        except APIConnectionError:
            print("Unable to connect to the LiteLLM proxy. Check LITELLM_BASE_URL and your network. Exiting.")
            sys.exit(1)
        except APIError as e:
            print(f"API error from model provider. Exiting.")
            sys.exit(1)
    return ""


if __name__ == "__main__":
    load_dotenv()

    required_vars = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "DATA_FILE_PATH"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}. Check your .env file. Exiting.")
        sys.exit(1)

    base_url = os.getenv("LITELLM_BASE_URL")
    api_key = os.getenv("LITELLM_API_KEY")
    model_name = os.getenv("MODEL_NAME")
    data_path = os.getenv("DATA_FILE_PATH")
    anomaly_threshold = float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0"))

    print(f"Active model via LiteLLM: {model_name}")

    df = load_and_validate_csv(data_path)
    print("\nColumns found in dataset:")
    for col in df.columns:
        print(f"  - {col}")

    business_question = input("\nEnter your business question: ")
    anomaly_column = input("Enter column name for anomaly detection: ")
    x_column = input("Enter independent variable column (x) for regression: ")
    y_column = input("Enter dependent variable column (y) for regression: ")

    if anomaly_column not in df.columns:
        print(f"Anomaly column '{anomaly_column}' not found in dataset. Exiting.")
        sys.exit(1)
    if x_column not in df.columns or y_column not in df.columns:
        print("One or both regression columns not found in dataset. Exiting.")
        sys.exit(1)

    anomalies = detect_anomalies(df, anomaly_column, anomaly_threshold)
    regression_results = run_ols_regression(df, x_column, y_column)
    chart_rec = recommend_visualization(business_question)

    print("\n--- Statistical Findings Summary ---")
    if anomalies:
        print(f"Anomalies detected (|Z| > {anomaly_threshold}): {len(anomalies)}")
        for a in anomalies:
            print(f"  Row {a['row_index']}: value={a['value']}, Z-score={a['z_score']}")
    else:
        print("No anomalies detected with the given threshold.")
    print(f"OLS Regression ({y_column} ~ {x_column}):")
    print(f"  R-squared:   {regression_results['r_squared']}")
    print(f"  Coefficient: {regression_results['coefficient']}")
    print(f"  P-value:     {regression_results['p_value']}")
    print(f"  Confidence:  {regression_results['confidence']}")
    print(f"Recommended visualization: {chart_rec}")
    print("------------------------------------\n")

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = build_analysis_prompt(business_question, anomalies, regression_results, chart_rec)
    response_text = call_llm_with_retry(client, model_name, prompt)

    print("ANALYSIS RESULT")
    print("---------------")
    print(response_text)