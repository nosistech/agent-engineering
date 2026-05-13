# MIT License, Copyright 2025 Packt

import json
import os
import random
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "ZONE_CONFIG_PATH", "SENSOR_LOG_PATH")


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def local_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_zones():
    zones, current = {}, None
    for raw in local_path(os.getenv("ZONE_CONFIG_PATH")).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1]
            zones[current] = {}
        elif current and ":" in line:
            key, value = line.strip().split(":", 1)
            zones[current][key] = float(value)
    return zones


def simulate(zone, config):
    target = (config["target_temp_min"] + config["target_temp_max"]) / 2
    occupancy = random.randint(0, int(config["max_occupancy"]))
    reading = {
        "zone": zone,
        "temperature": round(random.uniform(target - 3, target + 3), 1),
        "co2": random.randint(400, 700 + occupancy * 60),
        "occupancy": occupancy,
    }
    controls = {
        "hvac": "HEAT"
        if reading["temperature"] < config["target_temp_min"]
        else "COOL"
        if reading["temperature"] > config["target_temp_max"]
        else "NONE",
        "ventilation": "INCREASE" if reading["co2"] > config["co2_limit_warning"] else "NORMAL",
    }
    return {"reading": reading, "controls": controls}


def ask_model(cycle):
    body = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "You are a facilities assistant. Turn this sensor/control "
                        "data into a concise report for a facilities manager. "
                        "Output the report only.\n\n"
                        + json.dumps(cycle, indent=2)
                    ),
                }
            ],
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
    for attempt in range(2):
        try:
            with urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            if attempt:
                raise
            time.sleep(2)


def run_cycle(zones):
    cycle = {
        "timestamp": time.time(),
        "zones": [simulate(zone, config) for zone, config in zones.items()],
    }
    cycle["report"] = ask_model(cycle)
    log_path = local_path(os.getenv("SENSOR_LOG_PATH"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("a", encoding="utf-8").write(json.dumps(cycle) + "\n")
    return cycle


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()
    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    zones = load_zones()
    for index in range(1, int(os.getenv("SIMULATION_CYCLES", "2")) + 1):
        print(f"\n=== Cycle {index} ===")
        cycle = run_cycle(zones)
        for item in cycle["zones"]:
            reading, controls = item["reading"], item["controls"]
            print(
                f"{reading['zone']}: {reading['temperature']} C, CO2 {reading['co2']} ppm, "
                f"HVAC {controls['hvac']}, Ventilation {controls['ventilation']}"
            )
        print("\nFacility Report:")
        print(cycle["report"])


if __name__ == "__main__":
    main()
