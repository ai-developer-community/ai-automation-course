# Code standards

These are the rules for the code in this repository. They exist so an automation can be handed to a business and trusted to run without you. Claude Code reads them through `CLAUDE.md`.

## Shape of an automation

- An automation is one file in `automations/` with a function called `run`. The last line picks the trigger: `triggers.job(run)` or `triggers.webhook(run)`.
- Break `run` into small named steps. Each step does one thing and logs what it is doing.
- Shared behaviour goes in `automations/toolkit/`, one idea per file. An automation file should read as a list of steps, not as plumbing.
- Prefer a module with plain functions over a class. Use a class only when it holds data (a pydantic model or a dataclass) or state that has to travel together.

## Types

- Annotate every function: each argument and the return type. `ruff` (the `ANN` rules) fails the build when one is missing, and `pyright` checks they are right.
- Use built-in generics and `|`: `list[str]`, `dict[str, int]`, `str | None`.
- Check outside data at the edge with pydantic. A webhook payload becomes a model such as `Lead` before any work happens. Ask a model for structured output with `agent.ask(prompt, shape=SomeModel)`.
- Use `Any` only where a value really can be anything, such as JSON from an API, and say why in a comment.

## Settings and secrets

- Read settings with `settings.get("NAME")`, never `os.environ["NAME"]`. A missing setting raises `MissingSetting`, which the trigger logs as an ERROR so the alert fires.
- A webhook checks its own secret when it starts, so a bad deploy fails at once instead of on the first request.
- Secrets live in `.env` on your laptop and in Secret Manager on Google Cloud. Never put one in code, a log line or a commit.

## Logging

- Log with `log.write(severity, **fields)`. It writes one JSON line that Cloud Logging can filter, with the automation's name on every line. Never use a bare `print` in an automation.
- Use `INFO` for normal progress, `WARNING` for something skipped that the run survived, and `ERROR` only for a failure a person must look at. `alerts.sh` emails on ERROR.
- Log what was decided and why, not the whole payload. Keep personal data out of logs where you can.

## Failure

- Call every outside service through `retry.call`. It retries only temporary failures (a dropped connection, 429, 5xx) and fails at once on anything else.
- Make sending safe to repeat. Pass an idempotency key to email, and check the sheet for a duplicate before acting.
- Decide what must never be lost, and do it first. Speed to lead tells the team and saves the lead even if both models fail.
- A bad request from a caller is a 400. A fault on our side is a 500 and an ERROR. Don't let one look like the other.
- Every step that reaches the outside world asks `shadow.skip` first, so a new automation can run on real data and send nothing.

## AI steps

Use the first kind of step that can do the job:

1. Plain code, for anything with a rule.
2. A decision model (`decide.ask`), for a yes or no, a choice or a score.
3. A writing model called once (`agent.ask`), for text, in a shape the code can check.
4. An agent (`agent.run`), only when the steps can't be written down in advance.

Code checks every model's output before acting on it, and the thresholds live in code as named constants.

## Tests

- Every automation has tests in `tests/` that run with fakes from `conftest.py`. No test calls Google, Slack or Resend.
- Test the behaviour that matters to the business: a lead is never lost, a duplicate isn't emailed twice, a wrong token is rejected before any work.
- When you fix a bug, add the test that would have caught it.

## Checks

All three must pass before a change is done. GitHub runs them on every push.

```
uv run ruff check .    # lint, import order and missing type annotations
uv run pyright         # type check
uv run pytest -q       # tests
```
