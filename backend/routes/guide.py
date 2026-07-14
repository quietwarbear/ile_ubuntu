"""The Village Guide — a greeter/navigator, not a chatbot (Doc's framing).

Answers "how do I…" questions from a curated knowledge file
(guide_knowledge.md) and points people to the right page. Env-gated like
storage.py and sms.py: without ANTHROPIC_API_KEY the endpoints report
disabled and the frontend hides the widget entirely.

Privacy contract:
- v1 is help-only. The model sees the knowledge file, the asker's first
  name / role / intent, the page they're on, and their question — never
  their data, messages, progress, or anyone else's anything.
- The guide.asked event carries only the page (the stream is
  faculty-readable; questions may be personal).
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from middleware import get_current_user
from rate_limit import rate_limit
from events import emit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guide", tags=["guide"])

GUIDE_MODEL = os.environ.get("GUIDE_MODEL", "claude-haiku-4-5")
_KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "guide_knowledge.md"
try:
    KNOWLEDGE = _KNOWLEDGE_PATH.read_text()
except Exception:  # missing knowledge file — guide can still run, thinner
    KNOWLEDGE = "You are the Village Guide for Ilé Ubuntu, a living learning commons."

# Valid in-app routes the guide may point to; anything else is dropped so a
# hallucinated route can never become a broken "Take me there" button.
KNOWN_ROUTES = {
    "/dashboard", "/courses", "/live", "/cohorts", "/archives", "/portfolio",
    "/villages", "/community", "/learning-circles", "/spaces", "/blog",
    "/messages", "/family", "/settings", "/subscriptions",
    "/community-dashboard", "/teacher-dashboard", "/session-records",
    "/analytics", "/marketing", "/",
}

# Response format: plain prose, then a final "ROUTE: /path" (or "ROUTE: none")
# line. Deliberately not JSON — constrained JSON decoding truncated answers at
# unescaped inner quotes (e.g. the model writing: tap "Add to my portfolio").
FORMAT_RULES = (
    "Reply with your answer as plain text. Then, on the very last line, write "
    "ROUTE: followed by the single most relevant in-app route from the "
    "knowledge (for a 'Take me there' button), or ROUTE: none if no page "
    "applies. No other formatting."
)


def guide_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@router.get("/status")
def guide_status(current_user: dict = Depends(get_current_user)):
    return {"enabled": guide_enabled(), "greeting_name": (current_user.get("name") or "").split(" ")[0]}


@router.post("/ask")
async def ask_guide(request: Request, current_user: dict = Depends(get_current_user)):
    if not guide_enabled():
        raise HTTPException(status_code=503, detail="The guide is resting (not configured on this server).")
    # Generous for real use, tight enough to bound cost per person.
    rate_limit(request, "guide", max_requests=20, window_seconds=3600)

    data = await request.json()
    question = (data.get("question") or "").strip()[:500]
    page = (data.get("page") or "").strip()[:100]
    if len(question) < 2:
        raise HTTPException(status_code=400, detail="Ask me something!")

    persona = (
        f"The person asking is {current_user.get('name', 'a member')} "
        f"(role: {current_user.get('role', 'student')}, "
        f"joined as: {current_user.get('intent') or 'learner'})."
    )
    if page:
        persona += f" They are currently on the {page} page."

    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=GUIDE_MODEL,
            max_tokens=600,
            system=[
                # Stable knowledge first (cacheable), volatile persona after.
                {"type": "text", "text": KNOWLEDGE, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": persona + " " + FORMAT_RULES},
            ],
            messages=[{"role": "user", "content": question}],
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=503, detail="The guide is catching their breath — try again in a minute.")
    except anthropic.APIStatusError as exc:
        logger.warning("guide: API error %s", getattr(exc, "status_code", "?"))
        raise HTTPException(status_code=503, detail="The guide couldn't answer just now — please try again.")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="The guide couldn't answer just now — please try again.")

    if response.stop_reason == "refusal":
        return {"answer": "That's not something I can help with — a facilitator would be the right person to ask.", "route": None}

    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    answer, route = text, None
    lines = text.rsplit("\n", 1)
    if len(lines) == 2 and lines[1].strip().upper().startswith("ROUTE:"):
        answer = lines[0].strip()
        candidate = lines[1].split(":", 1)[1].strip()
        route = candidate if candidate.startswith("/") else None
    elif text.upper().startswith("ROUTE:"):
        # Degenerate single-line reply
        answer, route = "", text.split(":", 1)[1].strip()

    if route not in KNOWN_ROUTES:
        route = None
    if not answer:
        answer = "I'm not sure about that one — your facilitator will know. Is there something else I can point you to?"

    # No question text in meta — the event stream is faculty-readable.
    emit("guide.asked", current_user, "guide", None, {"page": page or None})
    return {"answer": answer, "route": route}
