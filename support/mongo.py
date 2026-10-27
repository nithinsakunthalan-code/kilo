"""MongoDB storage for chat logs and feedback.

Chat must never break because logging is down, so every function swallows errors and a short
circuit breaker skips MongoDB for 30 s after a failure instead of waiting for the timeout on every call.
"""
import logging
import time
import uuid
from datetime import datetime, timezone

from django.conf import settings

logger = logging.getLogger('support')

_client = None
_down_until = 0.0
BREAKER_SECONDS = 30


def get_db():
    """Return the Mongo database, or None when not configured / temporarily down."""
    global _client
    if not settings.MONGODB_URI or time.monotonic() < _down_until:
        return None
    if _client is None:
        from pymongo import MongoClient
        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    return _client[settings.MONGODB_DB]


def _trip(exc):
    global _down_until
    _down_until = time.monotonic() + BREAKER_SECONDS
    logger.error('MongoDB unavailable, skipping for %ss: %s', BREAKER_SECONDS, exc)


def _now():
    return datetime.now(timezone.utc)


def log_chat(session_id, user_message, reply, source, latency_ms, ip_hash, username=None, ticket=None,
             faq_id=None):
    """Store one chat exchange. Returns a message id (used to attach feedback)."""
    message_id = uuid.uuid4().hex
    db = get_db()
    if db is None:
        return message_id
    try:
        db.chat_logs.insert_one({
            'message_id': message_id, 'session_id': session_id, 'timestamp': _now(),
            'username': username, 'user_message': user_message, 'reply': reply, 'source': source,
            'faq_id': faq_id, 'ticket': ticket, 'latency_ms': latency_ms, 'ip_hash': ip_hash,
        })
    except Exception as exc:  # noqa: BLE001 - logging must never break chat
        _trip(exc)
    return message_id


def log_feedback(session_id, message_id, rating, comment=''):
    db = get_db()
    if db is None:
        return False
    try:
        db.feedback.insert_one({
            'session_id': session_id, 'message_id': message_id, 'rating': rating,
            'comment': comment, 'timestamp': _now(),
        })
        return True
    except Exception as exc:  # noqa: BLE001
        _trip(exc)
        return False


def ping():
    """Return 'ok', 'not_configured' or 'down' (used by the health page)."""
    if not settings.MONGODB_URI:
        return 'not_configured'
    db = get_db()
    if db is None:
        return 'down'
    try:
        db.command('ping')
        return 'ok'
    except Exception as exc:  # noqa: BLE001
        _trip(exc)
        return 'down'
