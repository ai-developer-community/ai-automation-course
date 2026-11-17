"""06: Hacker News for AI developers. Twice a day, which front page stories are worth an AI developer's time?

The business   a team that builds with AI and wants to keep up without reading Hacker News all day.
Today          someone scrolls the front page a few times a day, and most of it isn't about AI.
Trigger        scheduled, at 8am and 6pm every day.
Output         new rows in the "Hacker News" tab of the sheet: one for each story worth reading.

No agent here, and nothing is written. The steps are known in advance, so plain
code does them, and the one judgment goes to the decision model:

    plain code         reads the front page from Hacker News's own API, skips every story
                       already in the sheet, and saves the ones that pass
    a decision model   would someone who builds with AI want to read this? One request a
                       story, a fraction of a second each. The answer is a probability.

The code sets the bar. KEEP is how sure the model must be, and every row saves
the score next to the story, so you can read the sheet and move the bar.

Safe to run at any time: a story is saved once, however long it stays on the front page.

    uv run python automations/06_hacker_news.py
"""

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx

from toolkit import decide, retry, sheets, triggers

TAB = "Hacker News"
API = "https://hacker-news.firebaseio.com/v0"  # Hacker News's own API. No key, no login
TOP = 30  # how far down the front page to read. The first page is 30 stories
KEEP = 0.5  # save a story when the decision model says it is at least this likely to be relevant

RELEVANT = decide.yes_no(
    "Would a software developer who builds products with AI models want to read this story?",
    yes="It is about AI models, agents, coding with AI, tools and libraries for building with AI, "
    "machine learning research or hardware, or AI news that changes what developers can build",
    no="It is general technology, science, business or politics news with no direct link to building with AI",
)


def fetch(path: str) -> Any:  # the API returns JSON: a story, or a list of ids
    """One call to the Hacker News API."""
    return retry.call(
        lambda: httpx.get(f"{API}/{path}.json", timeout=15).raise_for_status().json()
    )


def relevance(story: dict) -> float:
    """The chance this story is one an AI developer wants, from 0 to 1. Judged on the headline and the site."""
    site = urlsplit(story.get("url", "")).hostname or "news.ycombinator.com"
    answers = decide.ask(f"Headline: {story['title']}\nSite: {site}", relevant=RELEVANT)
    return float(answers["relevant"].value)


def run() -> dict:
    # 1. The front page, best first, without the stories a run before this one saved.
    have = {
        row[1] for row in sheets.read(TAB) if len(row) > 1
    }  # every row, so it works with or without a header
    new = [
        story_id for story_id in fetch("topstories")[:TOP] if str(story_id) not in have
    ]

    found = datetime.now(timezone.utc).isoformat(timespec="minutes")
    added = []
    for story_id in new:
        # 2. Read the story. The front page also holds job adverts, and a story can be removed.
        story = fetch(f"item/{story_id}")
        if (
            not story
            or story.get("type") != "story"
            or story.get("dead")
            or story.get("deleted")
        ):
            continue

        # 3. Is it for us? The model gives the probability, and KEEP decides.
        score = relevance(story)
        if score < KEEP:
            continue

        # 4. Save it. "Ask HN" and "Show HN" posts can have no link of their own, so they point at the discussion.
        discussion = f"https://news.ycombinator.com/item?id={story_id}"
        sheets.add(
            TAB,
            [
                found,
                str(story_id),
                story["title"],
                story.get("url") or discussion,
                discussion,
                story.get("score", 0),
                story.get("descendants", 0),
                round(score, 2),
            ],
        )
        added.append(story["title"])
    return {"checked": len(new), "added": added}


if __name__ == "__main__":
    triggers.job(run)
