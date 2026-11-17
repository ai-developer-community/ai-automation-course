"""01: manual. Hello world as a job you start by hand.

A job starts, does its work and stops. This one does nothing useful on purpose:
it shows the shape every automation in this repo has. A function called run,
a few steps that each log what they are doing, and a last line that says what
starts it.

    On your laptop:   uv run python automations/01_manual.py
    On Cloud Run:     gcloud run jobs execute hello-manual --region $REGION --wait
"""

from toolkit import log, triggers


def step_1() -> str:
    log.write("INFO", step="step_1", message="Getting the input")
    return "world"


def step_2(name: str) -> str:
    log.write("INFO", step="step_2", message="Doing the work", name=name)
    return f"Hello, {name}!"


def run() -> dict:
    name = step_1()
    message = step_2(name)
    return {"message": message}


if __name__ == "__main__":
    triggers.job(run)
