# Copyright (C) 2026 Vertel Sverige AB.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Database free logic for ``social.content.source``.

Everything here is a pure function of its arguments: no ``self``, no ORM, no
environment. It can be imported and unit tested without a database, following
the ``*_core`` convention already used by ``render_service/render_core.mjs``.

All datetimes are naive and are treated as UTC, exactly like Odoo stores them.
"""

import calendar
import re
from datetime import datetime, timedelta

WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# Matches {{ token }} with optional surrounding whitespace.
TOKEN_RE = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}')


def float_to_time_parts(time_of_day):
    """Convert an Odoo float time to an (hour, minute, second) tuple.

    8.783333 becomes (8, 47, 0). Values are clamped inside a single day.
    """
    total = int(round(float(time_of_day or 0.0) * 3600))
    total = max(0, min(total, 24 * 3600 - 1))
    return total // 3600, (total % 3600) // 60, total % 60


def _at_time(day, time_of_day):
    hour, minute, second = float_to_time_parts(time_of_day)
    return datetime(day.year, day.month, day.day, hour, minute, second)


def _clamp_day(year, month, day):
    return max(1, min(int(day or 1), calendar.monthrange(year, month)[1]))


def _add_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def compute_next_occurrence(from_dt, interval_type, weekday=None,
                            day_of_month=1, time_of_day=8.0):
    """Return the first scheduled datetime strictly after ``from_dt``.

    ``interval_type`` is one of 'daily', 'weekly', 'monthly'. ``weekday`` is a
    key of :data:`WEEKDAYS` and only used for 'weekly'; ``day_of_month`` is
    only used for 'monthly' and is clamped to the length of the target month,
    so day 31 in February lands on the 28th (29th on a leap year).
    """
    if not isinstance(from_dt, datetime):
        raise TypeError('from_dt must be a datetime, got %r' % (from_dt,))

    if interval_type == 'daily':
        candidate = _at_time(from_dt, time_of_day)
        if candidate <= from_dt:
            candidate += timedelta(days=1)
        return candidate

    if interval_type == 'weekly':
        target = WEEKDAYS.index(weekday) if weekday in WEEKDAYS else 0
        candidate = _at_time(from_dt, time_of_day)
        candidate += timedelta(days=(target - candidate.weekday()) % 7)
        if candidate <= from_dt:
            candidate += timedelta(days=7)
        return candidate

    if interval_type == 'monthly':
        year, month = from_dt.year, from_dt.month
        day = _clamp_day(year, month, day_of_month)
        candidate = _at_time(datetime(year, month, day), time_of_day)
        if candidate <= from_dt:
            year, month = _add_month(year, month)
            day = _clamp_day(year, month, day_of_month)
            candidate = _at_time(datetime(year, month, day), time_of_day)
        return candidate

    raise ValueError('Unknown interval_type %r' % (interval_type,))


def pick_next_id(candidate_ids, posted_ids):
    """Pick the next id to post from an ordered pool.

    Returns a ``(next_id, restarted)`` tuple. The first candidate that has not
    been posted yet wins, so rotation is stable and never repeats a record
    while the pool still holds an unposted one. When every candidate has been
    posted the rotation starts over at the first candidate and ``restarted``
    is True. An empty pool returns ``(None, False)``.
    """
    posted = set(posted_ids or ())
    for candidate in candidate_ids:
        if candidate not in posted:
            return candidate, False
    if candidate_ids:
        return candidate_ids[0], True
    return None, False


def extract_tokens(template):
    """Return the ordered, de-duplicated {{ token }} names in ``template``."""
    seen = []
    for name in TOKEN_RE.findall(template or ''):
        if name not in seen:
            seen.append(name)
    return seen


def render_message(template, values):
    """Substitute {{ token }} placeholders in ``template`` with ``values``.

    Unknown tokens are replaced by an empty string. No expression evaluation
    happens here, so a template can never execute anything.
    """
    if not template:
        return ''

    def _replace(match):
        return str(values.get(match.group(1), '') or '')

    return TOKEN_RE.sub(_replace, template)
