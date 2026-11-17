"""Fakes for the outside world, so the tests run in seconds with no Google account."""
import importlib.util
from pathlib import Path

import pytest

from toolkit import agent, decide, mail, sheets, slack, web

AUTOMATIONS = Path(__file__).parents[1] / "automations"


def load(name: str):
    """Import an automation by file name. Files that start with a number can't be imported the usual way."""
    spec = importlib.util.spec_from_file_location(name, AUTOMATIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class World:
    """Everything the automations touched: sheet rows, Slack messages and emails."""

    def __init__(self):
        self.tabs: dict[str, list[list]] = {}
        self.slack: list[str] = []
        self.emails: list[dict] = []
        self.answer = None  # what the fake writing model says, or an exception it raises
        self.decisions = None  # what the fake decision model says: {name: decide.Answer}, a function of the text, or an exception
        self.agent = None  # what the fake agent does: a function that is handed the tools by name
        self.search = ("", [])  # what a fake search finds: a summary and its links
        self.pages: dict[str, str] = {}  # the fake web: link -> text


@pytest.fixture
def world(monkeypatch) -> World:
    w = World()
    monkeypatch.setenv("SHADOW", "false")
    monkeypatch.setattr(sheets, "read", lambda tab: w.tabs.get(tab, []))
    monkeypatch.setattr(sheets, "add", lambda tab, row: w.tabs.setdefault(tab, []).append(row))
    monkeypatch.setattr(slack, "post", lambda text: w.slack.append(text) or True)

    def send(to, subject, text, key):
        w.emails.append({"to": to, "subject": subject, "text": text, "key": key})
        return True

    def ask(prompt, shape=None):
        if isinstance(w.answer, Exception):
            raise w.answer
        return w.answer(prompt) if callable(w.answer) else w.answer

    def decide_ask(text, **questions):
        if isinstance(w.decisions, Exception):
            raise w.decisions
        return w.decisions(text) if callable(w.decisions) else w.decisions

    monkeypatch.setattr(mail, "send", send)
    monkeypatch.setattr(agent, "ask", ask)
    monkeypatch.setattr(decide, "ask", decide_ask)
    monkeypatch.setattr(agent, "run", lambda goal, tools, turns=20: w.agent({tool.__name__: tool for tool in tools}))
    monkeypatch.setattr(agent, "search", lambda query: w.search)
    monkeypatch.setattr(web, "read", lambda link: (link, w.pages[link]))
    return w
