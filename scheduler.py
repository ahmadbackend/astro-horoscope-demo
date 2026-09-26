"""Delivery scheduling: which users should get their horoscope right now?

In production an hourly job (Celery beat / cron) calls `users_due()` and queues
one generate-and-send task per user. Each user is stored with an IANA time zone
(derived from their birth city or set by them), so "7am" is always *their* 7am,
including across daylight-saving changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

DELIVERY_HOUR = 7


@dataclass
class User:
    id: int
    name: str
    tz: str                        # e.g. "Africa/Cairo"
    last_sent: date | None = None  # user's local date of the last delivery


def local_now(user: User, now_utc: datetime) -> datetime:
    return now_utc.astimezone(ZoneInfo(user.tz))


def is_due(user: User, now_utc: datetime, hour: int = DELIVERY_HOUR) -> bool:
    """Due if it is past the delivery hour locally and nothing was sent today.

    Using ">= hour" plus a last_sent check (instead of "== hour") means a
    missed run or a worker outage still delivers later that morning, and a
    retry never sends twice.
    """
    now = local_now(user, now_utc)
    return now.hour >= hour and user.last_sent != now.date()


def users_due(users: list[User], now_utc: datetime) -> list[User]:
    return [u for u in users if is_due(u, now_utc)]
