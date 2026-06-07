import re
from urllib.parse import urlparse

import validators

_WWW_RE = re.compile(r"^www\.", re.I)


class UrlValidationError(ValueError):
    pass


def normalize_url(raw: str) -> tuple[str, str]:
    """Return (canonical_url, domain). Raises UrlValidationError."""
    if not raw or not isinstance(raw, str):
        raise UrlValidationError("URL is required")

    url = raw.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    if not validators.url(url):
        raise UrlValidationError(f"Invalid URL: {raw}")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError("Only http and https URLs are supported")

    host = parsed.hostname
    if not host:
        raise UrlValidationError("URL must include a valid host")

    domain = _WWW_RE.sub("", host.lower())
    canonical = f"{parsed.scheme}://{host}"
    if parsed.port and (
        (parsed.scheme == "http" and parsed.port != 80)
        or (parsed.scheme == "https" and parsed.port != 443)
    ):
        canonical = f"{parsed.scheme}://{host}:{parsed.port}"
    path = parsed.path or "/"
    if parsed.query:
        canonical = f"{canonical}{path}?{parsed.query}"
    else:
        canonical = f"{canonical}{path}"

    return canonical, domain
