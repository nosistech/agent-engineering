# MIT License, Copyright 2025 Packt

import json
import os
import random
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_env() -> None:
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def require_env() -> None:
    needed = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "ZONE_CONFIG_PATH", "SENSOR_LOG_PATH"]
    missing = [key for key in needed if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_DIR / path


def load_zone_config(path: Path) -> dict:
    zones = {}
    current_zone = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_zone = line[:-1]
            zones[current_zone] = {}
            continue
        if current_zone and ":" in line:
            key, value = line.strip().split(":", 1)
            zones[current_zone][key] = float(value.strip())
    return zones


def simulate_reading(zone: str, config: dict) -> dict:
    target_mid = (config["target_temp_min"] + config["target_temp_max"]) / 2
    max_occupancy = int(config["max_occupancy"])
    occupancy = random.randint(0, max_occupancy)
    return {
        "zone": zone,
        "temperature": round(random.uniform(target_mid - 3, target_mid + 3), 1),
        "co2": random.randint(400, 400 + occupancy * 60 + 300),
        "occupancy": occupancy,
    }


def decide_controls(reading: dict, config: dict) -> dict:
    temp = reading["temperature"]
    co2 = reading["co2"]

    if temp < config["target_temp_min"]:
        hvac = "HEAT"
    elif temp > config["target_temp_max"]:
        hvac = "COOL"
    else:
        hvac = "NONE"

    ventilation = "INCREASE" if co2 > config["co2_limit_warning"] else "NORMAL"
    return {"hvac": hvac, "ventilation": ventilation}


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


def narrate(cycle: dict) -> str:
    prompt = (
        "You are a facilities assistant. Turn this sensor/control data into a concise "
        "plain-English report for a non-technical facilities manager. Output the report only.\n\n"
        + json.dumps(cycle, indent=2)
    )
    return call_llm(prompt)


def append_log(cycle: dict) -> None:
    path = project_path(os.getenv("SENSOR_LOG_PATH"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(cycle) + "\n")


def run_cycle(zones: dict) -> dict:
    zone_results = []
    for zone, config in zones.items():
        reading = simulate_reading(zone, config)
        controls = decide_controls(reading, config)
        zone_results.append({"reading": reading, "controls": controls})

    cycle = {"timestamp": time.time(), "zones": zone_results}
    cycle["report"] = narrate(cycle)
    append_log(cycle)
    return cycle


def main() -> None:
    load_env()
    require_env()
    zones = load_zone_config(project_path(os.getenv("ZONE_CONFIG_PATH")))
    cycles = int(os.getenv("SIMULATION_CYCLES", "2"))

    for index in range(1, cycles + 1):
        print(f"\n=== Cycle {index}/{cycles} ===")
        cycle = run_cycle(zones)
        for zone in cycle["zones"]:
            reading = zone["reading"]
            controls = zone["controls"]
            print(
                f"{reading['zone']}: {reading['temperature']} C, "
                f"CO2 {reading['co2']} ppm, HVAC {controls['hvac']}, "
                f"Ventilation {controls['ventilation']}"
            )
        print("\nFacility Report:")
        print(cycle["report"])


if __name__ == "__main__":
    main()
