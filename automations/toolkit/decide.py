"""Decide: quick judgments from a decision model. Google's Gemini Decisions API.

A decision model doesn't write. You give it some text and a few questions, and
each answer comes back as a value and a probability that code can branch on:

    yes_no   is this true?         The answer is the chance it's yes, from 0 to 1.
    choice   which one of these?   The answer is the option it picked.
    score    where on this scale?  The answer is the level, counted from 0.

Every question about the same text goes in one request. It takes a fraction of
a second and costs far less than a model that writes. The model gives the
probability and your code sets the threshold, so your code decides what
"sure enough" means.

    answers = decide.ask(
        "Hi, can you automate our invoices? We need it this month.",
        real=decide.yes_no("Is this a genuine enquiry?"),
        topic=decide.choice("What is it about?", {"invoices": "Bills and payments", "other": "Anything else"}),
    )
    answers["real"].value   # 0.97
    answers["topic"].value  # "invoices"

This is the one place the course needs a Google API key. Google launched the
Decisions API on its developer platform first, and on Google Cloud it still
answered "404 Method not found" on 14 November 2026. So set GEMINI_API_KEY, from
Google AI Studio. With no key it tries Google Cloud as the service account, the
way agent.py signs in, so the key can go once Google adds it there.
"""
import os
from dataclasses import dataclass
from functools import cache
from typing import Any, cast

from google import genai

from toolkit import agent, retry, usage

MODEL = os.environ.get("DECISION_MODEL", "gemini-decision-1")


# A question in the shape the API takes. The helpers below build it; the API checks it.
Question = dict[str, Any]


@dataclass
class Answer:
    value: float | str  # yes_no: the chance it's yes. choice: the option picked. score: the level, from 0
    confidence: float   # how sure the model is of that answer, from 0 to 1


def yes_no(question: str, yes: str = "", no: str = "") -> Question:
    """A yes or no question. `yes` and `no` can say what each answer means."""
    spec: Question = {"type": "noul", "instructions": question}  # "noul" is the API's name for a yes or no question
    if yes and no:
        spec["criteria"] = {"true_description": yes, "false_description": no}
    return spec


def choice(question: str, options: dict[str, str]) -> Question:
    """Pick exactly one. `options` maps each option's name to what it means."""
    return {"type": "choice", "instructions": question, "criteria": options}


def score(question: str, levels: list[str]) -> Question:
    """Place it on a scale. `levels` describes each step, lowest first: the first is 0, the next is 1."""
    return {"type": "score", "instructions": question, "criteria": levels}


@cache
def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY")
    # v1beta: the Decisions API is in preview, and the library's default version answers 404 for it.
    return genai.Client(api_key=key, http_options={"api_version": "v1beta"}) if key else agent.client()


def ask(text: str, **questions: Question) -> dict[str, Answer]:
    """Ask every question about one piece of text, in one request. Answers come back under the same names."""
    response = retry.call(lambda: _client().decisions.create(model=MODEL, input=text, questions=cast(Any, questions)))
    if response.usage:
        usage.add(response.usage.total_tokens or 0)
    if not response.answers:
        raise RuntimeError(f"the decision model gave no answers: {response.prompt_feedback}")
    # Each answer keeps its value in a field named after its type: noul, choice or score.
    # The library also types an "unknown" answer with no confidence; the API only sends the three we ask for.
    return {name: Answer(getattr(answer, answer.type), answer.confidence)  # pyright: ignore[reportAttributeAccessIssue]
            for name, answer in response.answers.items()}
