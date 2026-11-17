"""01: manual. Hello world as a job you start by hand.

A job starts, does its work and stops. This one does nothing useful on purpose:
it shows the shape every automation in this repo has. A function called run,
and a last line that says what starts it.

    On your laptop:   uv run python automations/01_manual.py
    On Cloud Run:     gcloud run jobs execute hello-manual --region $REGION --wait
"""

from toolkit import triggers


def step_1():
    pass


def step_2():
    pass


def run() -> dict:
    return {"message": "This is a manual automation run"}


if __name__ == "__main__":
    triggers.job(run)
