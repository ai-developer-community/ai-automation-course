"""Log: one JSON line per event, the format Cloud Logging reads.

Every line says which automation wrote it. `severity` is what Cloud Logging
filters on, and the alert in alerts.sh watches for ERROR.
"""
import json
import sys
from pathlib import Path

NAME = Path(sys.argv[0]).stem  # the file that was run, e.g. 04_speed_to_lead


def write(severity: str, **fields: object) -> None:
    print(json.dumps({"severity": severity, "automation": NAME, **fields}, default=str), flush=True)
