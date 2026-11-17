"""Hacker News and the decision model are faked: a small front page, and a model that likes headlines with "AI" in them."""
import pytest
from conftest import load

from toolkit.decide import Answer

news = load("06_hacker_news")
SCORE = 7  # the column of a Hacker News row that holds the model's score

FRONT_PAGE = {
    1: {"type": "story", "title": "A new open AI model for code", "url": "https://models.example/code", "score": 420, "descendants": 96},
    2: {"type": "story", "title": "SpaceX catches the booster", "url": "https://space.example/catch", "score": 900, "descendants": 300},
    3: {"type": "story", "title": "Ask HN: How do you test AI agents?", "score": 55, "descendants": 40},
    4: {"type": "job", "title": "An AI startup is hiring", "url": "https://jobs.example/ai"},
    5: None,  # removed after it reached the front page
}


@pytest.fixture(autouse=True)
def hacker_news(world, monkeypatch):
    """Returns the list of every call made to the fake Hacker News API."""
    calls = []

    def fetch(path):
        calls.append(path)
        return list(FRONT_PAGE) if path == "topstories" else FRONT_PAGE[int(path.removeprefix("item/"))]

    monkeypatch.setattr(news, "fetch", fetch)
    world.decisions = lambda text: {"relevant": Answer(0.93 if "AI" in text else 0.04, 0.9)}
    return calls


def test_only_the_stories_for_ai_developers_are_saved(world):
    result = news.run()
    assert result == {"checked": 5, "added": ["A new open AI model for code", "Ask HN: How do you test AI agents?"]}
    first, second = world.tabs["Hacker News"]
    assert first[1:] == ["1", "A new open AI model for code", "https://models.example/code",
                         "https://news.ycombinator.com/item?id=1", 420, 96, 0.93]
    # No link of its own, so both links point at the discussion.
    assert second[3] == second[4] == "https://news.ycombinator.com/item?id=3"


def test_a_story_is_saved_once_however_many_times_the_job_runs(world, hacker_news):
    news.run()
    hacker_news.clear()
    assert news.run() == {"checked": 3, "added": []}
    assert len(world.tabs["Hacker News"]) == 2
    assert "item/1" not in hacker_news  # a saved story isn't even fetched again


def test_job_adverts_and_removed_stories_never_reach_the_model(world):
    judged = []
    world.decisions = lambda text: judged.append(text) or {"relevant": Answer(0.9, 0.9)}
    news.run()
    assert len(judged) == 3 and not any("hiring" in text for text in judged)


def test_the_model_sees_the_headline_and_the_site(world):
    judged = []
    world.decisions = lambda text: judged.append(text) or {"relevant": Answer(0.1, 0.9)}
    news.run()
    assert judged[0] == "Headline: A new open AI model for code\nSite: models.example"
    assert judged[2].endswith("Site: news.ycombinator.com")


def test_the_code_sets_the_bar_not_the_model(world, monkeypatch):
    world.decisions = lambda text: {"relevant": Answer(0.4, 0.6)}
    assert news.run()["added"] == []  # 0.4 is under KEEP
    monkeypatch.setattr(news, "KEEP", 0.4)
    assert len(news.run()["added"]) == 3
    assert world.tabs["Hacker News"][0][SCORE] == 0.4


def test_if_the_model_fails_the_job_fails_and_the_next_run_picks_up_the_rest(world):
    def model(text):
        if "Ask HN" in text:
            raise RuntimeError("the decision model is down")
        return working(text)

    working, world.decisions = world.decisions, model
    with pytest.raises(RuntimeError):  # triggers.job logs an ERROR, and the alert fires
        news.run()
    assert [row[1] for row in world.tabs["Hacker News"]] == ["1"]  # what was saved before the failure is kept

    world.decisions = working
    assert news.run()["added"] == ["Ask HN: How do you test AI agents?"]
