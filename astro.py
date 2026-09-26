"""Astrology engine: natal chart, daily transits and transit-to-natal aspects.

Uses the Swiss Ephemeris (pyswisseph) with its built-in Moshier ephemeris,
so no extra data files are needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import swisseph as swe

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

# angle -> name
ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}

# Transit orbs in degrees. The Moon moves ~13°/day, so it gets a wider orb.
DEFAULT_ORB = 3.0
MOON_ORB = 5.0

FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


@dataclass
class Position:
    name: str
    longitude: float
    retrograde: bool = False

    @property
    def sign(self) -> str:
        return SIGNS[int(self.longitude // 30) % 12]

    @property
    def degree_in_sign(self) -> float:
        return self.longitude % 30

    def describe(self) -> str:
        rx = " (retrograde)" if self.retrograde else ""
        return f"{self.name} {self.degree_in_sign:.0f}° {self.sign}{rx}"


@dataclass
class Chart:
    positions: dict[str, Position]
    ascendant: Position | None = None
    house_cusps: list[float] = field(default_factory=list)  # 12 cusps, index 0 = 1st house

    def house_of(self, longitude: float) -> int | None:
        """Return the house (1-12) a zodiac longitude falls in."""
        if len(self.house_cusps) != 12:
            return None
        for i in range(12):
            start = self.house_cusps[i]
            end = self.house_cusps[(i + 1) % 12]
            span = (end - start) % 360
            if (longitude - start) % 360 < span:
                return i + 1
        return None


@dataclass
class Aspect:
    transit: Position
    natal: Position
    aspect: str
    orb: float
    natal_house: int | None = None

    def describe(self) -> str:
        house = f", in your natal house {self.natal_house}" if self.natal_house else ""
        return (
            f"Transiting {self.transit.describe()} {self.aspect} natal "
            f"{self.natal.describe()} (orb {self.orb:.1f}°{house})"
        )


def to_julian_day(dt_utc: datetime) -> float:
    hour = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


def planet_positions(jd: float) -> dict[str, Position]:
    positions = {}
    for name, pid in PLANETS.items():
        values, _ = swe.calc_ut(jd, pid, FLAGS)
        longitude, speed = values[0], values[3]
        positions[name] = Position(name, longitude % 360, retrograde=speed < 0)
    return positions


def natal_chart(birth_date: date, birth_time: time, tz: str, lat: float, lon: float) -> Chart:
    local = datetime.combine(birth_date, birth_time, tzinfo=ZoneInfo(tz))
    jd = to_julian_day(local.astimezone(ZoneInfo("UTC")))
    positions = planet_positions(jd)

    # Placidus is undefined near the poles; fall back to whole-sign houses.
    try:
        cusps, ascmc = swe.houses(jd, lat, lon, b"P")
    except swe.Error:
        cusps, ascmc = swe.houses(jd, lat, lon, b"W")
    cusps = list(cusps)[-12:]  # some versions return 13 values with an unused index 0

    return Chart(
        positions=positions,
        ascendant=Position("Ascendant", ascmc[0] % 360),
        house_cusps=[c % 360 for c in cusps],
    )


def transits_at(moment_utc: datetime) -> dict[str, Position]:
    return planet_positions(to_julian_day(moment_utc))


def find_aspects(transits: dict[str, Position], natal: Chart) -> list[Aspect]:
    """Transit-to-natal aspects, tightest first."""
    found = []
    for t in transits.values():
        orb_limit = MOON_ORB if t.name == "Moon" else DEFAULT_ORB
        for n in natal.positions.values():
            separation = abs(t.longitude - n.longitude) % 360
            separation = min(separation, 360 - separation)
            for angle, name in ASPECTS.items():
                orb = abs(separation - angle)
                if orb <= orb_limit:
                    found.append(Aspect(t, n, name, orb, natal.house_of(t.longitude)))
    return sorted(found, key=lambda a: a.orb)
