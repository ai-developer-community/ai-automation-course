"""The agent loop, with a fake model that follows a script."""
from types import SimpleNamespace

import pytest
from google.genai import types

from toolkit import agent


def says(*parts) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))])


def call(name: str, **args) -> types.Part:
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def words(text: str) -> types.Part:
    return types.Part(text=text)


@pytest.fixture
def model(monkeypatch):
    """model(first, second, ...) sets what the fake model says on each turn, and returns what it was sent."""
    def script(*responses):
        left, sent = list(responses), []

        def generate_content(model, contents, config):
            sent.append(list(contents))
            return left.pop(0)

        monkeypatch.setattr(agent, "client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
        return sent
    return script


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def test_the_agent_runs_the_tool_the_model_asks_for_and_shows_it_the_result(model):
    sent = model(says(call("add", a=2, b=3)), says(words("The answer is 5.")))
    assert agent.run("What is 2 + 3?", tools=[add]) == "The answer is 5."
    result = sent[1][-1].parts[0].function_response  # the last thing the model saw on its second turn
    assert result.name == "add" and result.response == {"result": 5, "turns_left": 19}


def test_a_tool_that_fails_is_reported_to_the_model_so_it_can_try_again(model):
    sent = model(says(call("add", a=2)), says(call("add", a=2, b=3)), says(words("5")))
    assert agent.run("What is 2 + 3?", tools=[add]) == "5"
    assert sent[1][-1].parts[0].function_response.response["result"].startswith("That failed:")


def test_the_loop_always_ends(model):
    model(*[says(call("add", a=1, b=1)) for _ in range(3)])
    assert agent.run("Keep adding.", tools=[add], turns=3) == "Stopped: out of turns."
