"""See the decision model work on its own: one enquiry in, three answers out.

    uv run python tools/triage.py
    uv run python tools/triage.py "CHEAP SEO!!! We will get you to number 1 on Google"
    uv run python tools/triage.py "Can you build us a mobile app?"
    uv run python tools/triage.py "Our invoices are three weeks behind and suppliers are chasing us. Can you automate them?"

It asks the same three questions speed to lead asks, and prints each answer, how
sure the model is, and what the code does with it. Nothing is sent or saved.
"""
import importlib.util
import sys
import time
from pathlib import Path

AUTOMATIONS = Path(__file__).parents[1] / "automations"
sys.path.insert(0, str(AUTOMATIONS))
from toolkit import decide, usage  # noqa: E402

# Speed to lead holds the questions and the thresholds. Its file name starts with a number, so load it by path.
spec = importlib.util.spec_from_file_location("speed_to_lead", AUTOMATIONS / "04_speed_to_lead.py")
assert spec and spec.loader
lead = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lead)

message = " ".join(sys.argv[1:]) or "We re-type every delivery note into our system. Can you help us automate that?"
start = time.monotonic()
answers = decide.ask(f"Name: Sam Price\nCompany: Price Logistics\nMessage: {message}", **lead.QUESTIONS)
took = round((time.monotonic() - start) * 1000)
real, service, urgency = answers["real"], answers["service"], answers["urgency"]

if service.confidence < lead.SURE:
    then = "not sure enough, so the writing model picks"
elif service.value == lead.NOT_FOR_US:
    then = "a person replies, and the writing model is never called"
else:
    then = "the writing model is told to offer it"
rows = [
    ("real", f"{real.value:.2f}", real, "spam: saved, nobody pinged" if real.value < lead.SPAM_BELOW else "treated as a real lead"),
    ("service", service.value, service, then),
    ("urgency", f"{urgency.value:.1f} of 2", urgency, "flagged urgent in Slack" if urgency.value >= lead.URGENT else "not flagged"),
]

print(f"\n{message}\n")
for name, value, answer, meaning in rows:
    print(f"  {name:8} {value:22} {answer.confidence:4.0%} sure   {meaning}")
print(f"\n  one request, {took} ms, {usage.tokens()} tokens\n")
