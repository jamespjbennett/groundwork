"""Session ID utilities.

A session groups related code changes within one working sitting. The
extension generates a UUID on activation and passes it with every
request to /analyse. The API records that id verbatim — the rotation
logic lives client-side.

This module provides the small helpers a client (the VS Code extension,
or any future surface) needs to manage that lifecycle: creating fresh
ids and deciding when an existing one has gone stale.
"""

import uuid
from datetime import datetime, timedelta, timezone

# A session ends after this much idle time. The next analyse call should
# come in on a freshly-generated id so the digest can group activity by
# sitting rather than by extension lifetime.
SESSION_TIMEOUT = timedelta(minutes=30)


def new_session_id() -> str:
    """Return a fresh UUID4 session id."""
    return str(uuid.uuid4())


def is_expired(last_activity_iso: str | None, *, now: datetime | None = None) -> bool:
    """True when the last activity is older than SESSION_TIMEOUT, or unknown.

    `last_activity_iso` is an ISO-8601 timestamp string (the format the
    store writes to `entries.created_at`). `now` is overridable for tests.
    """
    if not last_activity_iso:
        return True
    last = datetime.fromisoformat(last_activity_iso)
    current = now or datetime.now(timezone.utc)
    return (current - last) > SESSION_TIMEOUT
