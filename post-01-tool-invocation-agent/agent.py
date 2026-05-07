## MIT License, Copyright 2025 Packt

import os
import sys
import json
import time
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # headless rendering
import matplotlib.pyplot as plt
from openai import OpenAI
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Environment & startup validation
# ----------------------------------------------------------------------
load_dotenv()

REQUIRED_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "DATA_FILE_PATH",
    "OUTPUT_DIR",
]

def check_environment() -> None:
    """Verify all required environment variables are present."""
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")

# ----------------------------------------------------------------------
# LiteLLM call helper
# ----------------------------------------------------------------------
def call_llm(prompt: str) -> str | None:
    """Send a prompt to the LiteLLM proxy and return the response text."""
    client = OpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
        base_url=os.getenv("LITELLM_BASE_URL"),
    )
    model = os.getenv("MODEL_NAME")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            # detect rate‑limit errors (provider‑agnostic)
            error_str = str(exc).lower()
            is_rate_limit = "rate limit" in error_str or "429" in error_str
            if is_rate_limit and attempt < max_retries:
                wait = 2 ** attempt
                print(f"[WARNING] Rate limited. Waiting {wait}s before retry ({attempt}/{max_retries})...")
                time.sleep(wait)
            elif attempt == max_retries:
                print(f"[ERROR] LLM call failed after {max_retries} attempts: {exc}")
                return None
            else:
                print(f"[ERROR] LLM call error (attempt {attempt}): {exc}")
                return None

# ----------------------------------------------------------------------
# Tool functions
# ----------------------------------------------------------------------
def load_csv(file_path: str) -> pd.DataFrame:
    """Load a CSV file and return a DataFrame."""
    try:
        df = pd.read_csv(file_path)
        print(f"[SUCCESS] Loaded {len(df)} rows from {os.path.basename(file_path)}")
        return df
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}. Please check DATA_FILE_PATH.")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[ERROR] Could not load CSV: {type(exc).__name__} – {exc}")
        return pd.DataFrame()

def group_by_and_aggregate(df: pd.DataFrame,
                          group_by_col: str,
                          agg_col: str,
                          agg_func: str = "sum") -> pd.DataFrame | None:
    """Group DataFrame by a column and aggregate another column."""
    if df.empty:
        print("[ERROR] No data to aggregate – DataFrame is empty.")
        return None

    if group_by_col not in df.columns:
        print(f"[ERROR] Column '{group_by_col}' not found. Available columns: {', '.join(df.columns)}")
        return None
    if agg_col not in df.columns:
        print(f"[ERROR] Column '{agg_col}' not found. Available columns: {', '.join(df.columns)}")
        return None

    valid_funcs = ["sum", "mean", "count"]
    if agg_func not in valid_funcs:
        print(f"[WARNING] Unsupported aggregation '{agg_func}'. Falling back to 'sum'.")
        agg_func = "sum"

    try:
        grouped = df.groupby(group_by_col)[agg_col].agg(agg_func).reset_index()
        print(f"[SUCCESS] Aggregated {agg_col} by {group_by_col} using {agg_func}.")
        return grouped
    except Exception as exc:
        print(f"[ERROR] Aggregation failed: {type(exc).__name__} – {exc}")
        return None

def plot_bar_chart(df: pd.DataFrame,
                   x_col: str,
                   y_col: str,
                   title: str,
                   output_path: str) -> str | None:
    """Generate and save a bar chart. Returns the output path on success."""
    try:
        if x_col not in df.columns or y_col not in df.columns:
            missing = [c for c in [x_col, y_col] if c not in df.columns]
            print(f"[ERROR] Missing columns for bar chart: {', '.join(missing)}")
            return None

        plt.figure(figsize=(10, 6))
        plt.bar(df[x_col], df[y_col], color="#4A90D9")
        plt.title(title)
        plt.xlabel(x_col.replace("_", " ").title())
        plt.ylabel(y_col.replace("_", " ").title())
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        print(f"[SUCCESS] Bar chart saved to {output_path}")
        return output_path
    except Exception as exc:
        print(f"[ERROR] Bar chart creation failed: {type(exc).__name__} – {exc}")
        return None

def plot_line_chart(df: pd.DataFrame,
                    x_col: str,
                    y_col: str,
                    title: str,
                    output_path: str) -> str | None:
    """Generate and save a line chart with markers. Returns the output path on success."""
    try:
        if x_col not in df.columns or y_col not in df.columns:
            missing = [c for c in [x_col, y_col] if c not in df.columns]
            print(f"[ERROR] Missing columns for line chart: {', '.join(missing)}")
            return None

        plt.figure(figsize=(10, 6))
        plt.plot(df[x_col], df[y_col], marker="o", linestyle="-", color="#4A90D9")
        plt.title(title)
        plt.xlabel(x_col.replace("_", " ").title())
        plt.ylabel(y_col.replace("_", " ").title())
        plt.xticks(rotation=45, ha="right")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        print(f"[SUCCESS] Line chart saved to {output_path}")
        return output_path
    except Exception as exc:
        print(f"[ERROR] Line chart creation failed: {type(exc).__name__} – {exc}")
        return None

# ----------------------------------------------------------------------
# Tool registry
# ----------------------------------------------------------------------
TOOL_REGISTRY = {
    "load_csv": {
        "function": load_csv,
        "description": "Load a CSV file into a pandas DataFrame.",
        "input_schema": {"file_path": "string"},
        "output_schema": "pandas DataFrame or empty DataFrame",
        "status": "active",
    },
    "group_by_and_aggregate": {
        "function": group_by_and_aggregate,
        "description": "Group a DataFrame by a column and aggregate another column (sum, mean, count).",
        "input_schema": {"df": "DataFrame", "group_by_col": "string", "agg_col": "string", "agg_func": "string"},
        "output_schema": "DataFrame or None",
        "status": "active",
    },
    "plot_bar_chart": {
        "function": plot_bar_chart,
        "description": "Save a bar chart to disk.",
        "input_schema": {"df": "DataFrame", "x_col": "string", "y_col": "string", "title": "string", "output_path": "string"},
        "output_schema": "file path string or None",
        "status": "active",
    },
    "plot_line_chart": {
        "function": plot_line_chart,
        "description": "Save a line chart to disk.",
        "input_schema": {"df": "DataFrame", "x_col": "string", "y_col": "string", "title": "string", "output_path": "string"},
        "output_schema": "file path string or None",
        "status": "active",
    },
}

# ----------------------------------------------------------------------
# Query parsing
# ----------------------------------------------------------------------
def parse_query(query: str) -> dict | None:
    """Parse a plain‑English query to extract metric, dimension, and chart type."""
    lower = query.lower()

    # ---- metric mapping ----
    metric = None
    if "spend" in lower:
        metric = "spend"
    elif "click" in lower:
        metric = "clicks"
    elif "conversion" in lower:
        metric = "conversions"
    else:
        return None

    # ---- dimension mapping ----
    dimension = None
    if "by campaign" in lower or "which campaign" in lower or "campaign" in lower:
        dimension = "campaign_name"
    elif "over time" in lower or "trend" in lower or "time" in lower or "date" in lower:
        dimension = "date"
    else:
        return None

    # ---- chart type from dimension ----
    chart_type = "bar" if dimension == "campaign_name" else "line"

    return {
        "metric": metric,
        "dimension": dimension,
        "chart_type": chart_type,
    }

# ----------------------------------------------------------------------
# LiteLLM‑based intent extraction as fallback
# ----------------------------------------------------------------------
def extract_intent_fallback(query: str) -> dict | None:
    """Use the LLM to extract intent when keyword parsing fails."""
    prompt = (
        "Extract the metric and dimension from the user query for data visualization. "
        "The dataset has columns: date, campaign_name, spend, clicks, conversions, impressions. "
        "Available metrics: spend, clicks, conversions. "
        "Available dimensions: date (for time series) and campaign_name (for grouping by campaign). "
        "Respond only with a JSON object in this exact format without any extra text: "
        '{"metric": "<metric_name>", "dimension": "<dimension_name>", "chart_type": "<bar or line>"} '
        "If the query does not clearly indicate a valid metric and dimension, respond with {\"error\": \"invalid\"}.\n"
        f"User query: {query}"
    )

    response = call_llm(prompt)
    if response is None:
        print("[ERROR] LLM fallback for intent extraction failed (no response).")
        return None

    # attempt to parse JSON from the response (strip possible markdown fences)
    cleaned = response.strip().removeprefix("```json").removeprefix("```").strip("`").strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[ERROR] LLM returned invalid JSON for intent extraction: {response}")
        return None

    if "error" in result:
        print("[INFO] LLM could not extract a valid intent from the query.")
        return None

    metric = result.get("metric")
    dimension = result.get("dimension")
    chart_type = result.get("chart_type", "bar")

    # validate the extracted values
    if metric not in ("spend", "clicks", "conversions"):
        print(f"[WARNING] LLM returned unsupported metric '{metric}'.")
        return None
    if dimension not in ("campaign_name", "date"):
        print(f"[WARNING] LLM returned unsupported dimension '{dimension}'.")
        return None

    return {"metric": metric, "dimension": dimension, "chart_type": chart_type}

# ----------------------------------------------------------------------
# Agent orchestrator
# ----------------------------------------------------------------------
def data_viz_agent(query: str) -> None:
    """Main data visualisation agent: think, plan, act."""
    data_path = os.getenv("DATA_FILE_PATH")
    output_dir = os.getenv("OUTPUT_DIR")

    # --- THINK: parse query ---
    plan = parse_query(query)
    if plan is None:
        print("[INFO] Keyword parsing failed; trying LLM fallback...")
        plan = extract_intent_fallback(query)

    if plan is None:
        print("[ERROR] Could not extract metric, dimension, or chart type from your query.")
        print("[INFO] Supported metrics: spend, clicks, conversions.")
        print("[INFO] Supported patterns: 'Show me [metric] by campaign' or 'What was the trend of [metric] over time?'")
        return

    # --- PLAN: build tool sequence ---
    steps = [
        ("load_csv", {"file_path": data_path}),
        ("group_by_and_aggregate", {
            "group_by_col": plan["dimension"],
            "agg_col": plan["metric"],
            "agg_func": "sum",
        }),
    ]

    chart_func = "plot_bar_chart" if plan["chart_type"] == "bar" else "plot_line_chart"
    chart_title = f"{plan['metric'].title()} by {plan['dimension'].replace('_', ' ').title()}"
    chart_filename = f"{plan['metric']}_by_{plan['dimension']}_{plan['chart_type']}.png"
    chart_path = os.path.join(output_dir, chart_filename)
    steps.append((chart_func, {
        "df": None,                 # placeholder, will receive the aggregated result
        "x_col": plan["dimension"],
        "y_col": plan["metric"],
        "title": chart_title,
        "output_path": chart_path,
    }))

    # --- ACT: execute the plan ---
    current_df = None
    for step_num, (tool_name, args) in enumerate(steps, start=1):
        tool_info = TOOL_REGISTRY.get(tool_name)
        if tool_info is None:
            print(f"[ERROR] Unknown tool '{tool_name}' – stopping.")
            return

        print(f"[INFO] Step {step_num}/{len(steps)}: {tool_name}")

        # inject current DataFrame into downstream tools
        if tool_name == "group_by_and_aggregate":
            args["df"] = current_df
            if current_df is None or current_df.empty:
                print(f"[ERROR] Cannot run {tool_name} because loaded data is missing or empty.")
                return

        if tool_name in ("plot_bar_chart", "plot_line_chart"):
            args["df"] = current_df
            if current_df is None or current_df.empty:
                print(f"[ERROR] Cannot run {tool_name} because the aggregated data is missing or empty.")
                return

        result = tool_info["function"](**args)

        # interpret result based on expected return type
        if tool_name == "load_csv":
            if result.empty:
                print("[ERROR] Data loading failed – cannot proceed.")
                return
            current_df = result

        elif tool_name == "group_by_and_aggregate":
            if result is None:
                print("[ERROR] Aggregation failed – cannot proceed.")
                return
            current_df = result

        elif tool_name in ("plot_bar_chart", "plot_line_chart"):
            if result is None:
                print("[ERROR] Chart generation failed.")
                return
            # success, no further state update needed

    print(f"[SUCCESS] Query processed: '{query}'")

# ----------------------------------------------------------------------
# Demo entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    check_environment()

    output_dir = os.getenv("OUTPUT_DIR")
    os.makedirs(output_dir, exist_ok=True)

    demo_queries = [
        "Show me spend by campaign",
        "What was the trend of clicks over time?",
        "Tell me something interesting",
    ]

    results_summary = []
    for query in demo_queries:
        print(f"\n{'='*60}\n[INFO] Demo query: \"{query}\"")
        try:
            data_viz_agent(query)
            results_summary.append((query, "SUCCESS"))
        except Exception as e:
            print(f"[ERROR] Unexpected failure: {e}")
            results_summary.append((query, "FAILED"))

    print("\n[INFO] Demo run complete. Summary:")
    for q, status in results_summary:
        print(f"       [{status}] {q}")
    print(f"[INFO] Output files (if any) are in: {output_dir}")