import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# normalise an n8n language label to our message language codes
LANGUAGE_MAP = {
    "darija": "ar",
    "derja": "ar",
    "tunisien": "ar",
    "tunisienne": "ar",
    "arabe tunisien": "ar",
    "arabic": "ar",
    "ar": "ar",
    "french": "fr",
    "fr": "fr",
    "english": "en",
    "en": "en",
}

# --- Fast Circuit Breaker Configuration ---
N8N_CONNECT_TIMEOUT = 1.5
N8N_REQUEST_TIMEOUT = 2.5
FAILURE_THRESHOLD = 2
COOLDOWN_SECONDS = 30.0

_consecutive_failures: int = 0
_cooldown_until: float = 0.0
_circuit_open: bool = False


def is_circuit_open() -> bool:
    """Check if the n8n circuit breaker is currently OPEN."""
    global _circuit_open
    if _circuit_open:
        now = time.monotonic()
        if now < _cooldown_until:
            return True
        # Cooldown expired -> transitions to HALF-OPEN (allow a probe call)
        _circuit_open = False
    return False


def record_n8n_failure() -> None:
    """Record an HTTP/connection failure and trip the circuit if threshold is reached."""
    global _consecutive_failures, _circuit_open, _cooldown_until
    _consecutive_failures += 1
    if _consecutive_failures >= FAILURE_THRESHOLD:
        _circuit_open = True
        _cooldown_until = time.monotonic() + COOLDOWN_SECONDS
        logger.warning(
            "n8n circuit breaker OPENED: tripping for %.1fs after %d consecutive failures",
            COOLDOWN_SECONDS,
            _consecutive_failures,
        )


def record_n8n_success() -> None:
    """Reset failure counts and close the circuit on successful response."""
    global _consecutive_failures, _circuit_open, _cooldown_until
    _consecutive_failures = 0
    _circuit_open = False
    _cooldown_until = 0.0


def reset_circuit_breaker() -> None:
    """Forced reset of circuit breaker state (useful for tests)."""
    global _consecutive_failures, _circuit_open, _cooldown_until
    _consecutive_failures = 0
    _circuit_open = False
    _cooldown_until = 0.0


def get_circuit_state() -> dict:
    """Return circuit breaker status for observability."""
    return {
        "is_open": is_circuit_open(),
        "consecutive_failures": _consecutive_failures,
        "cooldown_until": _cooldown_until,
    }


def _normalise_language(language: str | None) -> str:
    if not language:
        return "fr"
    return LANGUAGE_MAP.get(language.strip().lower(), language.strip().lower()[:2])


async def generate_with_n8n(
    *,
    user_message: str,
    conversation_history: str,
    product_context: str,
    preferred_language: str | None = "fr",
    system_prompt: str = "",
) -> dict | None:
    """Send the conversation to the n8n Darija workflow and return its reply.

    Returns None if n8n is not configured, unreachable, or in cooldown, so callers
    can immediately fall back to the direct LLM tool-calling pipeline without delay.
    """
    if not settings.n8n_webhook_url:
        return None

    if is_circuit_open():
        logger.info(
            "n8n circuit is OPEN (cooldown active until %.1fs); fast-failing to native AI",
            _cooldown_until,
        )
        return None

    payload = {
        "user_message": user_message,
        "conversation_history": conversation_history,
        "product_context": product_context,
        "preferred_language": preferred_language or "fr",
        "system_prompt": system_prompt,
    }
    headers = {"Content-Type": "application/json"}
    if settings.n8n_api_key:
        headers["X-N8N-Api-Key"] = settings.n8n_api_key

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(N8N_REQUEST_TIMEOUT, connect=N8N_CONNECT_TIMEOUT)
        ) as client:
            resp = await client.post(
                settings.n8n_webhook_url, json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            record_n8n_success()
    except (httpx.HTTPError, Exception) as e:
        record_n8n_failure()
        logger.warning("n8n request failed (%s); failing back to native AI pipeline", e)
        return None

    reply = data.get("reply") or data.get("response") or ""
    if not reply:
        logger.warning("n8n returned an empty reply")
        return None

    return {
        "reply": reply,
        "language": _normalise_language(
            data.get("language") or data.get("detected_language")
        ),
    }
