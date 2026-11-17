"""The agent picks its own steps, so the tests play the agent and check what the tools let it do."""
from conftest import load

research = load("05_research_agent")
ACME = "https://news.example/acme-raises-5m"


def test_the_agent_saves_what_it_found_and_the_team_is_told(world):
    world.search = ("Acme Freight raised £5m this week.", [ACME])

    def agent(tools):
        assert ACME in tools["search"]("UK logistics funding this week")
        assert tools["save"]("Acme Freight", "Raised £5m", ACME, "2026-11-11").startswith("Saved Acme Freight")
        return "Found one company."

    world.agent = agent
    assert research.run() == {"added": ["Acme Freight"], "note": "Found one company."}
    assert world.tabs["Prospects"][0][1:] == ["Acme Freight", "Raised £5m", "2026-11-11", ACME, "new"]
    assert world.slack == ["1 new prospects in the sheet today: Acme Freight"]


def test_a_company_already_in_the_sheet_is_refused(world):
    world.tabs["Prospects"] = [["date", "company"], ["2026-11-10", "Acme Freight"]]
    world.search = ("Acme Freight raised £5m.", [ACME])

    def agent(tools):
        tools["search"]("acme")
        assert tools["save"]("acme freight ", "Raised £5m", ACME, "unknown") == "Not saved: we already have acme freight."
        return "Nothing new."

    world.agent = agent
    assert research.run()["added"] == []
    assert world.slack == []  # nothing new, so no message


def test_a_link_the_agent_never_saw_is_refused(world):
    def agent(tools):
        assert tools["save"]("Made Up Ltd", "Hired a CTO", "https://made-up.example/news", "unknown").startswith("Not saved")
        return "Nothing."

    world.agent = agent
    assert research.run()["added"] == []
    assert "Prospects" not in world.tabs


def test_a_page_the_agent_opened_counts_as_a_source(world):
    world.pages[ACME] = "Acme Freight has raised £5m to open a second warehouse."

    def agent(tools):
        assert "second warehouse" in tools["read"](ACME)
        tools["save"]("Acme Freight", "Raised £5m", ACME, "2026-11-11")
        return "Found one."

    world.agent = agent
    assert research.run()["added"] == ["Acme Freight"]


def test_the_daily_limit_stops_the_agent(world, monkeypatch):
    monkeypatch.setattr(research, "MAX_NEW", 1)
    world.search = ("Two companies raised money.", [ACME])

    def agent(tools):
        tools["search"]("funding")
        tools["save"]("Acme Freight", "Raised £5m", ACME, "unknown")
        assert "limit" in tools["save"]("Bolt Haulage", "Raised £2m", ACME, "unknown")
        return "Stopped at the limit."

    world.agent = agent
    assert research.run()["added"] == ["Acme Freight"]
