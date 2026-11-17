"""The decision model, faked: what one request carries, and how the answers come back."""
from types import SimpleNamespace

import pytest
from google.genai.decisions import ChoiceAnswer, CreateDecisionResponse, NoulAnswer, ScoreAnswer

from toolkit import decide


@pytest.fixture
def sent(monkeypatch):
    request = {}

    def create(model, input, questions):
        request.update(model=model, input=input, questions=questions)
        return CreateDecisionResponse(answers={
            "real": NoulAnswer(noul=0.97, confidence=0.97),
            "topic": ChoiceAnswer(choice="invoices", confidence=0.8, probabilities={"invoices": 0.8, "other": 0.2}),
            "urgency": ScoreAnswer(score=1.6, confidence=0.7, legend={}, probabilities={"1": 0.4, "2": 0.6}),
        })

    monkeypatch.setattr(decide, "_client", lambda: SimpleNamespace(decisions=SimpleNamespace(create=create)))
    return request


def test_every_question_goes_in_one_request_and_each_answer_comes_back_by_name(sent):
    answers = decide.ask(
        "Can you automate our invoices? We need it this month.",
        real=decide.yes_no("Is this a genuine enquiry?", yes="They ask for help", no="Spam"),
        topic=decide.choice("What is it about?", {"invoices": "Bills and payments", "other": "Anything else"}),
        urgency=decide.score("How soon?", ["No hurry", "This year", "This month"]),
    )
    assert sent["input"].startswith("Can you automate") and list(sent["questions"]) == ["real", "topic", "urgency"]
    assert sent["questions"]["real"] == {"type": "noul", "instructions": "Is this a genuine enquiry?",
                                         "criteria": {"true_description": "They ask for help", "false_description": "Spam"}}
    assert answers["real"] == decide.Answer(0.97, 0.97)      # the chance it's yes
    assert answers["topic"] == decide.Answer("invoices", 0.8)  # the option picked
    assert answers["urgency"] == decide.Answer(1.6, 0.7)     # the level, counted from 0


def test_no_answers_is_an_error_not_a_guess(monkeypatch):
    empty = SimpleNamespace(decisions=SimpleNamespace(create=lambda **request: CreateDecisionResponse()))
    monkeypatch.setattr(decide, "_client", lambda: empty)
    with pytest.raises(RuntimeError):
        decide.ask("hello", real=decide.yes_no("Is this real?"))
