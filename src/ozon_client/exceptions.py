"""Ozon client exceptions."""


class OzonError(Exception):
    """Base error."""


class TransportError(OzonError):
    """Network/CDP-level failure."""


class AntibotBlocked(OzonError):
    """Target returned 403 + ozon-antibot. Retry via browser oracle."""

    def __init__(self, incident_id=None, challenge_url=None, timeout_sec=None):
        self.incident_id = incident_id
        self.challenge_url = challenge_url
        self.timeout_sec = timeout_sec
        super().__init__(
            f"antibot 403 (incident={incident_id}). "
            "The browser oracle must re-warm the session."
        )


class NotFound(OzonError):
    """404 from target."""


class AuthRequired(OzonError):
    """401 — endpoint needs a logged-in session."""


class RateLimited(OzonError):
    """429 / throttle observed."""

    def __init__(self, retry_after=None):
        self.retry_after = retry_after
        super().__init__(f"rate limited (retry_after={retry_after})")


class ParseError(OzonError):
    """Response shape unexpected — target markup changed."""
