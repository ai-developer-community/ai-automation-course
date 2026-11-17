import pytest
from conftest import load

from toolkit.decide import Answer

lead = load("04_speed_to_lead")
FORM = {"name": "Sam Price", "email": "sam@example.com", "company": "Price Logistics",
        "message": "We re-type every delivery note. Can you help?"}
STATUS = 7  # the column of the Leads row that holds the status


def sorted_as(real=0.97, service="Automation audit", sure=0.9, urgency=0.3):
    """What the fake decision model says about an enquiry."""
    return {"real": Answer(real, max(real, 1 - real)), "service": Answer(service, sure), "urgency": Answer(urgency, 0.8)}


def good_proposal(prompt):
    return lead.Proposal(fits=True, subject="Your delivery notes",
                         body="Hi Sam, an Automation audit (£3,000) would find what to automate first.")


@pytest.fixture(autouse=True)
def a_real_enquiry(world):
    world.decisions = sorted_as()


def test_a_lead_gets_a_proposal_and_the_team_hears(world):
    world.answer = good_proposal
    assert lead.run(FORM)["status"] == "proposal sent"
    assert len(world.emails) == 1 and world.emails[0]["to"] == "sam@example.com"
    assert world.slack[0].startswith("New lead: Sam Price")
    assert world.slack[1] == "Proposal sent to Sam Price (Price Logistics): Your delivery notes"
    assert world.tabs["Leads"][0][STATUS:] == ["proposal sent", "Automation audit", 0.97, 0.3]


# The decision model sorts the enquiry, and the code decides what each answer means.

def test_the_writer_is_told_which_service_the_decision_model_picked(world):
    prompts = []
    world.answer = lambda prompt: prompts.append(prompt) or good_proposal(prompt)
    lead.run(FORM)
    assert "suggest the Automation audit service with its price" in prompts[0]


def test_spam_is_saved_but_nobody_is_pinged(world):
    world.decisions = sorted_as(real=0.02)
    assert lead.run(FORM)["status"] == "spam"
    assert world.slack == [] and world.emails == []
    assert world.tabs["Leads"][0][STATUS] == "spam"


def test_a_lead_that_only_might_be_spam_is_treated_as_real(world):
    world.decisions = sorted_as(real=0.3)  # a lost lead costs more than reading spam
    world.answer = good_proposal
    assert lead.run(FORM)["status"] == "proposal sent"


def test_work_we_do_not_do_goes_to_a_person_without_a_writing_call(world):
    prompts = []
    world.decisions = sorted_as(service="Not something we do")
    world.answer = prompts.append
    assert lead.run({**FORM, "message": "Can you build us a mobile app?"})["status"] == "needs a person"
    assert prompts == [] and world.emails == [] and len(world.slack) == 2


def test_an_unsure_pick_is_left_to_the_writer(world):
    prompts = []
    world.decisions = sorted_as(service="Support", sure=0.4)
    world.answer = lambda prompt: prompts.append(prompt) or good_proposal(prompt)
    assert lead.run(FORM)["status"] == "proposal sent"
    assert "suggest the one service that fits best" in prompts[0]


def test_an_urgent_lead_is_flagged_for_the_team(world):
    world.decisions = sorted_as(urgency=1.8)
    world.answer = good_proposal
    lead.run(FORM)
    assert world.slack[0].startswith("New lead (urgent): Sam Price")


def test_the_decision_model_fails_and_the_lead_still_gets_a_proposal(world):
    world.decisions = RuntimeError("decision model is down")
    world.answer = good_proposal
    assert lead.run(FORM)["status"] == "proposal sent"
    assert world.slack[0].startswith("New lead: Sam Price")
    assert world.tabs["Leads"][0][STATUS + 1:] == ["", "", ""]  # no answers, so none are written down


# The writing model's work is checked by code, and its failure never loses a lead.

def test_the_model_fails_and_the_lead_is_still_saved(world):
    world.answer = RuntimeError("model is down")
    assert lead.run(FORM)["status"] == "needs a person"
    assert world.emails == []
    assert len(world.slack) == 2  # the lead, then "needs a reply from a person"
    assert world.tabs["Leads"][0][STATUS] == "needs a person"


def test_the_same_lead_twice_sends_one_email(world):
    world.answer = good_proposal
    lead.run(FORM)
    assert lead.run(FORM)["status"] == "duplicate"
    assert len(world.emails) == 1


def test_a_made_up_price_is_never_sent(world):
    world.answer = lead.Proposal(fits=True, subject="Offer", body="We can do it all for £99.")
    assert lead.run(FORM)["status"] == "needs a person"
    assert world.emails == []


def test_every_price_in_the_list_can_be_quoted(world):
    # "From £12,000, quoted after..." in services.md: the comma after the price is not part of it.
    world.answer = lead.Proposal(fits=True, subject="One automation",
                                 body="Build one automation starts from £12,000, and support is £1,500 a month.")
    assert lead.run(FORM)["status"] == "proposal sent"


def test_nothing_fits_and_a_person_replies(world):
    world.answer = lead.Proposal(fits=False, subject="", body="")
    assert lead.run({**FORM, "message": "Can you build us a mobile app?"})["status"] == "needs a person"
    assert world.emails == []


def test_a_bad_form_is_refused_before_any_work(world):
    with pytest.raises(ValueError):
        lead.run({"name": "Sam", "email": "not an email", "message": "hi"})
    assert world.slack == [] and world.tabs == {}


def test_shadow_mode_writes_the_proposal_but_sends_nothing(world, monkeypatch):
    from toolkit import mail
    monkeypatch.setattr(mail, "send", lambda *a, **k: False)  # what the real send returns in shadow mode
    world.answer = good_proposal
    assert lead.run(FORM)["status"] == "proposal ready (shadow mode)"
    assert len(world.slack) == 1  # the lead. Nothing went, so the team isn't told it did


def test_every_service_in_the_price_list_is_an_option(world):
    assert list(lead.OFFERS) == ["Automation audit", "Build one automation", "Support", "Not something we do"]
