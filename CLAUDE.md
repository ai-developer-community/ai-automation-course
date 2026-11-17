# Advanced AI Automation course code

Read [STANDARDS.md](STANDARDS.md) before writing or changing any code here, and follow it.

Before you say a change is done, run all three checks and make sure they pass:

```
uv run ruff check .
uv run pyright
uv run pytest -q
```

The files in `automations/` are shown in the course video. Keep their shape (a `run` function and a last line that picks the trigger) so they still match what viewers see. Put shared behaviour in `automations/toolkit/`.

Never commit `.env` or any secret.
