import ipaddress
import re
from urllib.parse import urlparse

_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HOST_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def strip_html(value: str) -> str:
    """Defence-in-depth: remove HTML tags and control characters from text.

    The frontend already escapes output, but stripping tags on input prevents
    stored markup from ever reaching a raw render (e.g. the public widget).
    """
    cleaned = _TAG_RE.sub("", value)
    cleaned = _CONTROL_RE.sub("", cleaned)
    return cleaned.strip()


def normalize_domain(value: str) -> str:
    """Normalise an allowed-origin entry to a bare lowercase hostname."""
    host = value.strip().lower()
    if "://" in host:
        host = urlparse(host).hostname or ""
    host = host.rstrip(".")
    if not host or len(host) > 253 or not _HOST_RE.match(host):
        raise ValueError(f"invalid domain: {value!r}")
    return host


def _is_blocked_host(host: str) -> bool:
    host = host.strip("[]").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(
        (".local", ".internal", ".localhost")
    ):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_https_url(value: str) -> str:
    """Validate an outbound webhook URL to mitigate SSRF.

    Requires https and rejects loopback/link-local/private IP literals and
    internal hostnames so a tenant cannot point server-side requests at
    internal services or cloud metadata endpoints.
    """
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValueError("URL must use https")
    if not parsed.hostname:
        raise ValueError("URL must include a host")
    if _is_blocked_host(parsed.hostname):
        raise ValueError("URL host is not allowed")
    return value
