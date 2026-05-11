# MIT License, Copyright 2025 Packt

import os
import sys
import time
import json
import yaml
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────
#  Startup: environment and configuration
# ──────────────────────────────────────────────

REQUIRED_ENV_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "ZONE_CONFIG_PATH",
    "SENSOR_LOG_PATH",
    "SIMULATION_CYCLES",
    "CYCLE_INTERVAL_SECONDS",
]

def validate_and_get_env():
    """Validate all required environment variables and return them."""
    missing = [var for var in REQUIRED_ENV_VARS if os.getenv(var) is None]
    if missing:
        print("ERROR: Missing required environment variables:")
        for m in missing:
            print(f"  - {m}")
        print("Please set them in a .env file and try again.")
        sys.exit(1)
    return {var: os.getenv(var) for var in REQUIRED_ENV_VARS}

# ──────────────────────────────────────────────
#  Zone configuration loading and validation
# ──────────────────────────────────────────────

ZONE_REQUIRED_FIELDS = [
    "target_temp_min",
    "target_temp_max",
    "co2_limit_warning",
    "co2_limit_critical",
    "max_occupancy",
    "deadband_degrees",
]

def load_zone_config(path):
    """Load and validate zone configuration from a YAML file."""
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        print("ERROR: Zone configuration file must contain a mapping of zone names to settings.")
        sys.exit(1)
    validated = {}
    for zone_name, zone_cfg in raw.items():
        missing = [f for f in ZONE_REQUIRED_FIELDS if f not in zone_cfg]
        if missing:
            print(f"ERROR: Zone '{zone_name}' is missing required fields: {missing}")
            sys.exit(1)
        validated[zone_name] = zone_cfg
    return validated

# ──────────────────────────────────────────────
#  Sensor simulation
# ──────────────────────────────────────────────

def simulate_sensor_reading(zone_name, zone_config):
    """Generate a realistic sensor reading for a zone."""
    target_mid = (zone_config["target_temp_min"] + zone_config["target_temp_max"]) / 2
    temp = np.random.normal(loc=target_mid, scale=1.5)

    occupancy = np.random.poisson(lam=zone_config["max_occupancy"] * 0.3)
    occupancy = min(occupancy, zone_config["max_occupancy"])
    base_co2 = 400
    co2_per_person = 50
    co2 = int(np.random.normal(loc=base_co2 + occupancy * co2_per_person, scale=30))

    return {
        "zone_name": zone_name,
        "temperature": round(temp, 2),
        "co2": co2,
        "occupancy": occupancy,
        "timestamp": time.time(),
    }

# ──────────────────────────────────────────────
#  Proportional control with deadband
# ──────────────────────────────────────────────

def apply_proportional_control(reading, zone_config):
    """Compute HVAC and ventilation commands based on sensor reading."""
    temp = reading["temperature"]
    co2 = reading["co2"]
    deadband = zone_config["deadband_degrees"]
    target_min = zone_config["target_temp_min"]
    target_max = zone_config["target_temp_max"]
    co2_warning = zone_config["co2_limit_warning"]
    co2_critical = zone_config["co2_limit_critical"]

    midpoint = (target_min + target_max) / 2
    error = temp - midpoint
    hvac_command = "NONE"
    hvac_intensity = 0
    reason_temp = ""

    if abs(error) <= deadband:
        reason_temp = f"Temperature within deadband (+-{deadband} degrees C of {midpoint} degrees C)."
    else:
        effective_error = abs(error) - deadband
        scale = 5.0
        intensity = min(100, int((effective_error / scale) * 100))
        hvac_intensity = intensity

        if error > 0:
            hvac_command = "COOL_HIGH" if intensity > 50 else "COOL_LOW"
            reason_temp = (
                f"Temperature {temp} degrees C exceeds target maximum {target_max} degrees C by "
                f"{round(temp - target_max, 2)} degrees C. Cooling at {intensity} percent."
            )
        else:
            hvac_command = "HEAT_HIGH" if intensity > 50 else "HEAT_LOW"
            reason_temp = (
                f"Temperature {temp} degrees C below target minimum {target_min} degrees C by "
                f"{round(target_min - temp, 2)} degrees C. Heating at {intensity} percent."
            )

    if co2 <= co2_warning:
        vent_command = "NORMAL"
        reason_co2 = f"CO2 level {co2} ppm within acceptable limits (limit: {co2_warning} ppm)."
    elif co2 <= co2_critical:
        vent_command = "INCREASED"
        reason_co2 = f"CO2 level {co2} ppm elevated (above {co2_warning} ppm). Increasing ventilation."
    else:
        vent_command = "MAXIMUM"
        reason_co2 = f"CO2 level {co2} ppm critical (above {co2_critical} ppm). Maximum ventilation active."

    reason = f"{reason_temp} {reason_co2}".strip()

    return {
        "hvac_command": hvac_command,
        "hvac_intensity": hvac_intensity,
        "ventilation_command": vent_command,
        "reason": reason,
    }

# ──────────────────────────────────────────────
#  LLM report generation
# ──────────────────────────────────────────────

def build_facility_summary(all_zone_readings, all_zone_commands):
    """Construct a structured text block for the LLM prompt."""
    summary_lines = []
    for zone_name in all_zone_readings:
        reading = all_zone_readings[zone_name]
        cmd = all_zone_commands[zone_name]
        summary_lines.append(
            f"Zone: {zone_name}\n"
            f"  Temperature: {reading['temperature']} degrees C\n"
            f"  CO2: {reading['co2']} ppm\n"
            f"  Occupancy: {reading['occupancy']}\n"
            f"  HVAC Command: {cmd['hvac_command']} ({cmd['hvac_intensity']} percent)\n"
            f"  Ventilation: {cmd['ventilation_command']}\n"
            f"  Decision Reason: {cmd['reason']}\n"
        )
    return "\n".join(summary_lines)

def generate_facility_report(summary_text, client, model_name):
    """Call LLM via LiteLLM to produce a plain-English facility report."""
    system_prompt = (
        "You are a facilities management AI assistant for NosisTech LLC. "
        "Given the sensor data and control decisions below, write a concise "
        "plain-English status report for a non-technical facilities manager. "
        "Respond with the report only. No preamble. No reasoning. No explanation "
        "of your thought process. Start directly with the report content. "
        "Highlight any urgent alerts and recommend any necessary actions. "
        "Keep the report under 200 words."
    )
    max_attempts = 3
    backoff = 1
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": summary_text},
                ],
                temperature=0.3,
                max_tokens=800,
                stream=False,
            )
            message = response.choices[0].message
            content = message.content or ""
            reasoning = getattr(message, "reasoning_content", None) or ""
            report = content.strip() if content.strip() else reasoning.strip()
            # Strip DeepSeek chain-of-thought preamble if present
            lines = report.splitlines()
            clean_lines = []
            preamble_keywords = ("we are asked", "the data", "i need", "let me", "let's", "first,", "i'll", "we need", "looking at", "the report", "consolidate", "i'll write", "i will", "let's parse", "i should", "so i'll", "so the report")
            collecting = False
            for line in lines:
                if collecting:
                    clean_lines.append(line)
                elif line.strip() and not line.strip().lower().startswith(preamble_keywords):
                    collecting = True
                    clean_lines.append(line)
            report = "\n".join(clean_lines).strip() if clean_lines else report
            return report
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate limit" in error_str or "too many requests" in error_str
            if is_rate_limit:
                if attempt < max_attempts:
                    print(f"Rate limited. Retrying in {backoff}s (attempt {attempt}/{max_attempts})...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print("ERROR: Rate limit exceeded after multiple attempts. Exiting.")
                    sys.exit(1)
            elif "connection" in error_str or "connect" in error_str:
                print("ERROR: Unable to reach LiteLLM endpoint. Please verify LITELLM_BASE_URL and network connectivity.")
                sys.exit(1)
            else:
                print(f"ERROR: {e}")
                sys.exit(1)

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────

def log_cycle(cycle_data, log_path):
    """Append a structured JSON record to the sensor log file."""
    with open(log_path, "a") as f:
        f.write(json.dumps(cycle_data) + "\n")

# ──────────────────────────────────────────────
#  Main simulation loop
# ──────────────────────────────────────────────

def main():
    """Run the physical world sensing agent simulation."""
    load_dotenv()
    env = validate_and_get_env()

    print(f"Active Model: {env['MODEL_NAME']}")

    zone_configs = load_zone_config(env["ZONE_CONFIG_PATH"])
    zone_names = list(zone_configs.keys())

    client = OpenAI(
        base_url=env["LITELLM_BASE_URL"],
        api_key=env["LITELLM_API_KEY"],
    )

    num_cycles = int(env["SIMULATION_CYCLES"])
    interval = float(env["CYCLE_INTERVAL_SECONDS"])
    log_path = env["SENSOR_LOG_PATH"]

    for cycle in range(1, num_cycles + 1):
        print(f"\n{'=' * 40}\nCycle {cycle}/{num_cycles}\n{'=' * 40}")

        readings = {}
        for name in zone_names:
            readings[name] = simulate_sensor_reading(name, zone_configs[name])

        commands = {}
        for name in zone_names:
            commands[name] = apply_proportional_control(readings[name], zone_configs[name])

        summary = build_facility_summary(readings, commands)
        report = generate_facility_report(summary, client, env["MODEL_NAME"])

        cycle_record = {
            "cycle": cycle,
            "timestamp": time.time(),
            "readings": {k: {**v, "occupancy": int(v["occupancy"])} for k, v in readings.items()},
            "commands": commands,
            "llm_report": report,
        }
        log_cycle(cycle_record, log_path)

        print("Zone States and Commands:")
        for name in zone_names:
            r = readings[name]
            c = commands[name]
            print(
                f"  {name}: "
                f"Temp={r['temperature']} C, CO2={r['co2']} ppm, Occ={r['occupancy']} | "
                f"HVAC={c['hvac_command']} at {c['hvac_intensity']} pct, Vent={c['ventilation_command']}"
            )
        print(f"\nFacility Report:\n{report}")

        if cycle < num_cycles:
            time.sleep(interval)

    print("\nSimulation complete.")

if __name__ == "__main__":
    main()