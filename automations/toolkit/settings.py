"""Settings: read one setting, and fail clearly when it is missing.

On your laptop the settings come from .env. On Cloud Run deploy.sh passes them
in, and the secrets come from Secret Manager.

A missing setting is our mistake, not the caller's. It raises MissingSetting,
which the trigger logs as an ERROR, so the failure alert fires.
"""
import os


class MissingSetting(RuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(f"{name} is not set. Add it to .env, then run ./deploy.sh again")


def get(name: str) -> str:
    """A setting that must be there."""
    value = os.environ.get(name, "")
    if not value:
        raise MissingSetting(name)
    return value


def require(*names: str) -> None:
    """Check settings when an automation starts, before it accepts any work."""
    for name in names:
        get(name)
