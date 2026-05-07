from datetime import datetime, timedelta, timezone

from session_manager import SESSION_TIMEOUT, is_expired, new_session_id


def test_new_session_id_returns_string():
    assert isinstance(new_session_id(), str)


def test_new_session_id_returns_unique_values():
    a, b = new_session_id(), new_session_id()
    assert a != b


def test_is_expired_when_last_activity_unknown():
    assert is_expired(None) is True
    assert is_expired("") is True


def test_is_expired_false_for_recent_activity():
    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    last = (now - timedelta(minutes=5)).isoformat()
    assert is_expired(last, now=now) is False


def test_is_expired_false_just_before_timeout():
    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    last = (now - SESSION_TIMEOUT + timedelta(seconds=1)).isoformat()
    assert is_expired(last, now=now) is False


def test_is_expired_true_just_past_timeout():
    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    last = (now - SESSION_TIMEOUT - timedelta(seconds=1)).isoformat()
    assert is_expired(last, now=now) is True
