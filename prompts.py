"""Prompt building for the horoscope generator."""
from __future__ import annotations

from datetime import date

from astro import Aspect, Chart, Position

SYSTEM_PROMPT = """You are a warm, insightful astrologer writing a personal daily horoscope.

Rules:
- Base every statement on the transit data you are given. Do not invent placements.
- Address the reader by first name, in the second person.
- Translate astrology into everyday life: work, relationships, energy, inner state.
- Be empathetic and encouraging, never fearful or fatalistic. Frame hard aspects as growth.
- No medical, legal or financial predictions or advice.
- Mention at most two astrological terms, and explain them in plain words.
- Length: 150-220 words. Structure: one short opening line, two short paragraphs,
  then one practical "Focus for today:" line.
"""

MAX_ASPECTS = 5


def build_user_prompt(
    name: str,
    day: date,
    natal: Chart,
    transits: dict[str, Position],
    aspects: list[Aspect],
) -> str:
    sun, moon = natal.positions["Sun"], natal.positions["Moon"]
    rising = f", rising sign {natal.ascendant.sign}" if natal.ascendant else ""

    lines = [
        f"Reader: {name}",
        f"Date: {day.strftime('%A, %d %B %Y')}",
        f"Natal chart: Sun in {sun.sign}, Moon in {moon.sign}{rising}.",
        "",
        "Today's sky:",
        *[f"- {p.describe()}" for p in transits.values()],
        "",
        "Most exact transits to the natal chart today (tightest first):",
    ]
    top = aspects[:MAX_ASPECTS]
    if top:
        lines += [f"- {a.describe()}" for a in top]
    else:
        lines.append(f"- No close aspects today; focus on the Moon in {transits['Moon'].sign}.")

    lines += ["", f"Write {name}'s horoscope for today."]
    return "\n".join(lines)
