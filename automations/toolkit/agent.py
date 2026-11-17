"""Agent: a model that writes, searches, or works as an agent. Gemini on Vertex AI.

    agent.ask(prompt)         one question, one answer
    agent.search(query)       search Google, and get back what it found with the links
    agent.run(goal, tools)    give the model a goal and some tools, and let it pick the steps

There is no API key. On Cloud Run the client signs in as the service account the
automation runs as. On your laptop it uses your gcloud login.

VERTEX_LOCATION is where the model runs. "global" has every model, and new
models often start there. Set a region, such as europe-west2, to pin where a
customer's data is processed. Check the model you pick is offered in that region.
"""
import os
from collections.abc import Callable
from functools import cache
from typing import Any

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel

from toolkit import log, retry, usage

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
LOCATION = os.environ.get("VERTEX_LOCATION", "global")

@cache
def client() -> genai.Client:
    # Cloud Run sets GOOGLE_CLOUD_PROJECT (deploy.sh). On your laptop it's PROJECT, from .env.
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT")
    return genai.Client(vertexai=True, project=project, location=LOCATION)


def _generate(contents: types.ContentListUnionDict, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    """One call to the model, retried if the failure is temporary, with its tokens counted."""
    response = retry.call(lambda: client().models.generate_content(model=MODEL, contents=contents, config=config))
    if response.usage_metadata:
        usage.add(response.usage_metadata.total_token_count or 0)
    return response


def ask(prompt: str, shape: type[BaseModel] | None = None) -> Any:
    """Ask the model one thing.

    shape:  a pydantic class. The answer comes back as that class instead of text.
    """
    response = _generate(prompt, types.GenerateContentConfig(
        response_mime_type="application/json" if shape else None, response_schema=shape))
    if shape is None:
        return response.text
    if response.parsed is None:
        raise RuntimeError("the model did not answer in the expected shape")
    return response.parsed


def search(query: str) -> tuple[str, list[str]]:
    """Search Google. Returns a summary of what it found, and the links it came from."""
    response = _generate(f"Search Google and report what you find, with dates: {query}",
                         types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    found = response.candidates[0].grounding_metadata if response.candidates else None
    chunks = (found.grounding_chunks if found else None) or []
    links = [_real_link(chunk.web.uri) for chunk in chunks if chunk.web and chunk.web.uri]
    return response.text or "", list(dict.fromkeys(links))  # each link once, in the order found


def _real_link(link: str) -> str:
    """Search results come back as Google redirect links. Ask where one points, to get the page's real address."""
    try:
        return httpx.get(link, timeout=10).headers.get("location", link)
    except httpx.HTTPError:
        return link


def run(goal: str, tools: list, turns: int = 20) -> str:
    """Give the model a goal and some tools. It picks the steps: which tool to call, with what, and when to stop.

    tools:  plain Python functions. The model is shown each one's name, arguments and docstring.
    turns:  the most times the model may act, so the loop always ends.

    An agent is this loop and nothing more: ask the model what to do next, run the
    tool it asked for, show it the result, and ask again, until it answers in words.
    """
    named: dict[str, Callable[..., Any]] = {tool.__name__: tool for tool in tools}
    # Tell the library not to run the tools itself: this loop does it, so each step is logged and counted.
    config = types.GenerateContentConfig(
        tools=tools, automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    history = [types.Content(role="user", parts=[types.Part(text=goal)])]
    for turn in range(1, turns + 1):
        response = _generate(history, config)
        if not response.function_calls:
            return response.text or ""  # no tool asked for: the model is done
        if response.candidates and response.candidates[0].content:
            history.append(response.candidates[0].content)  # what the model asked for, so it sees its own turn
        results = []
        for call in response.function_calls:
            name = call.name or ""
            try:
                result = named[name](**(call.args or {}))
            except Exception as error:
                result = f"That failed: {error}"  # tell the model, so it can try something else
            log.write("INFO", turn=turn, tool=name, args=call.args, result=str(result)[:300])
            # The model can't count its own turns, so every result says how many are left.
            results.append(types.Part.from_function_response(
                name=name, response={"result": result, "turns_left": turns - turn}))
        history.append(types.Content(role="user", parts=results))
    return "Stopped: out of turns."
