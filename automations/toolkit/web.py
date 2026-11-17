"""Web: open a page and return its text. An agent uses it to check a source before relying on it."""
import html
import re

import httpx

from toolkit import retry

BROWSER = {"User-Agent": "Mozilla/5.0 (compatible; automations-course/1.0)"}


def read(link: str, limit: int = 4000) -> tuple[str, str]:
    """A page's address (after any redirects) and its text, cut to `limit` characters."""
    if not link.startswith("https://"):
        raise ValueError("only https links can be opened")  # no plain http, so not the cloud's own internal addresses

    def get() -> httpx.Response:
        return httpx.get(link, follow_redirects=True, timeout=15, headers=BROWSER).raise_for_status()

    page = retry.call(get)
    if page.url.scheme != "https":
        raise ValueError("the link redirected to a page that isn't https")  # the same rule, after redirects
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page.text)  # code and styling aren't words
    text = re.sub(r"(?s)<[^>]+>", " ", text)  # nor are the tags
    return str(page.url), re.sub(r"\s+", " ", html.unescape(text)).strip()[:limit]
