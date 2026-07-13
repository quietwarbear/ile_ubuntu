"""Text messaging (SMS / WhatsApp) via Twilio — the family digest's
highest-reach channel (eval §11.4): includes elders and caregivers who
don't do email, especially across the diaspora.

Same pattern as storage.py: configured entirely by env vars, and every
feature degrades gracefully when they're absent (digest stays email-only).

    TWILIO_ACCOUNT_SID     account SID (required to enable texting)
    TWILIO_AUTH_TOKEN      auth token (required)
    TWILIO_FROM_SMS        sender phone number in E.164, e.g. +15105551234
                           (required for the "sms" channel)
    TWILIO_FROM_WHATSAPP   WhatsApp sender, e.g. whatsapp:+14155238886
                           (required for the "whatsapp" channel)

Uses Twilio's plain REST API through `requests` (already a dependency) —
no SDK needed for one endpoint.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
_FROM_SMS = os.environ.get("TWILIO_FROM_SMS", "").strip()
_FROM_WHATSAPP = os.environ.get("TWILIO_FROM_WHATSAPP", "").strip()


def channel_enabled(channel: str) -> bool:
    """True when credentials and the sender for this channel are configured."""
    if not (_SID and _TOKEN):
        return False
    if channel == "sms":
        return bool(_FROM_SMS)
    if channel == "whatsapp":
        return bool(_FROM_WHATSAPP)
    return False


def enabled_channels() -> list:
    return [c for c in ("sms", "whatsapp") if channel_enabled(c)]


def send_text(to_phone: str, body: str, channel: str = "sms") -> bool:
    """Send one message. Never raises — a failed text must not break the
    digest run (email already went out). Returns True on acceptance."""
    if not channel_enabled(channel):
        return False
    if channel == "whatsapp":
        to, sender = f"whatsapp:{to_phone}", _FROM_WHATSAPP
    else:
        to, sender = to_phone, _FROM_SMS
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{_SID}/Messages.json",
            auth=(_SID, _TOKEN),
            data={"To": to, "From": sender, "Body": body},
            timeout=15,
        )
        if resp.status_code >= 400:
            logger.warning("Twilio %s send failed (%s): %s", channel, resp.status_code, resp.text[:200])
            return False
        return True
    except Exception:
        logger.exception("Twilio %s send raised", channel)
        return False
