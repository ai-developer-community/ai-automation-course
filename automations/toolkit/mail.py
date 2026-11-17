"""Email: send one message through Resend (resend.com). Any email API works the same way.

The API key is a secret. On Cloud Run it comes from Secret Manager.
"""

import httpx

from toolkit import retry, settings, shadow


def send(to: str, subject: str, text: str, key: str) -> bool:
    """Send an email. Returns whether it was sent: shadow mode sends nothing.

    key:  the same key for the same email. If a retry sends it twice, Resend
          delivers it once (its Idempotency-Key header).
    """
    if shadow.skip("send email", {"to": to, "subject": subject, "text": text}):
        return False
    retry.call(lambda: httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.get('RESEND_API_KEY')}", "Idempotency-Key": key},
        json={"from": settings.get("EMAIL_FROM"), "to": [to], "subject": subject, "text": text},
        timeout=15,
    ).raise_for_status())
    return True
