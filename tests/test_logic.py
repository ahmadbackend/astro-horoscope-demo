"""Tests for aspect detection, house placement, prompt building and scheduling.

swisseph is replaced with a small stub so these run without the C extension
and check our own logic, not the ephemeris.
"""
import sys
import types
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

stub = types.ModuleType("swisseph")
for i, n in enumerate(["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER",
                       "SATURN", "URANUS", "NEPTUNE", "PLUTO"]):
    setattr(stub, n, i)
stub.FLG_MOSEPH, stub.FLG_SPEED = 4, 256
stub.Error = type("Error", (Exception,), {})
stub.julday = lambda y, m, d, h: 2451545.0
stub.calc_ut = lambda jd, pid, flags: ((pid * 30.0 + 1, 0, 1, -0.1 if pid == 2 else 1.0), flags)
stub.houses = lambda jd, lat, lon, hsys: (tuple(float(i * 30) for i in range(12)), (15.0,) + (0.0,) * 7)
sys.modules["swisseph"] = stub  # always use the stub, even if pyswisseph is installed

from astro import Chart, Position, find_aspects, natal_chart, transits_at  # noqa: E402
from prompts import build_user_prompt  # noqa: E402
from scheduler import User, is_due  # noqa: E402


def natal(**lons):
    return Chart(positions={k: Position(k, v) for k, v in lons.items()},
                 house_cusps=[i * 30.0 for i in range(12)])


def test_signs_and_degrees():
    p = Position("Sun", 45.5)
    assert p.sign == "Taurus" and round(p.degree_in_sign, 1) == 15.5
    assert Position("Moon", 359.9).sign == "Pisces"


def test_aspects_detected_with_orb_and_wraparound():
    chart = natal(Sun=10.0, Moon=100.0)
    transits = {
        "Mars": Position("Mars", 358.0),    # 12° from Sun: no aspect
        "Venus": Position("Venus", 11.5),   # conjunction Sun, orb 1.5
        "Saturn": Position("Saturn", 191.0),  # opposition Sun, orb 1.0
        "Moon": Position("Moon", 14.0),     # conj Sun orb 4 (Moon orb 5 allows it)
        "Jupiter": Position("Jupiter", 14.0),  # conj Sun orb 4 (> 3, rejected)
    }
    found = find_aspects(transits, chart)
    pairs = [(a.transit.name, a.natal.name, a.aspect) for a in found]
    assert pairs[0] == ("Saturn", "Sun", "opposition")  # tightest first
    assert ("Venus", "Sun", "conjunction") in pairs
    assert ("Moon", "Sun", "conjunction") in pairs
    assert ("Jupiter", "Sun", "conjunction") not in pairs
    assert ("Saturn", "Moon", "square") in pairs  # 191 vs 100 = 91°


def test_conjunction_across_zero_aries():
    found = find_aspects({"Venus": Position("Venus", 359.0)}, natal(Sun=1.0))
    assert found and found[0].aspect == "conjunction" and round(found[0].orb, 1) == 2.0


def test_house_of_with_wrapping_cusps():
    chart = Chart(positions={}, house_cusps=[(300 + i * 30) % 360 for i in range(12)])
    assert chart.house_of(310) == 1
    assert chart.house_of(5) == 3   # 0-30 is the 3rd house here
    assert chart.house_of(299) == 12


def test_natal_chart_and_transits_use_ephemeris():
    chart = natal_chart(date(1995, 4, 12), datetime(2000, 1, 1, 8, 30).time(), "Africa/Cairo", 30.79, 31.0)
    assert chart.positions["Sun"].sign == "Aries" and chart.ascendant.sign == "Aries"
    assert len(chart.house_cusps) == 12
    assert transits_at(datetime(2026, 9, 26, 4, tzinfo=timezone.utc))["Mercury"].retrograde


def test_prompt_contains_chart_and_top_aspects():
    chart = natal(Sun=10.0, Moon=100.0)
    chart.ascendant = Position("Ascendant", 200.0)
    transits = {"Moon": Position("Moon", 12.0), "Venus": Position("Venus", 11.0)}
    prompt = build_user_prompt("Sara", date(2026, 9, 26), chart, transits, find_aspects(transits, chart))
    assert "Reader: Sara" in prompt and "Saturday, 26 September 2026" in prompt
    assert "Sun in Aries, Moon in Cancer, rising sign Libra" in prompt
    assert "Transiting Venus 11° Aries conjunction natal Sun 10° Aries (orb 1.0°" in prompt


def test_prompt_without_aspects():
    prompt = build_user_prompt("Sara", date(2026, 9, 26), natal(Sun=10.0, Moon=100.0),
                               {"Moon": Position("Moon", 245.0)}, [])
    assert "No close aspects today; focus on the Moon in Sagittarius." in prompt


def test_scheduler_uses_each_users_local_morning():
    cairo, ny = User(1, "A", "Africa/Cairo"), User(2, "B", "America/New_York")
    now = datetime(2026, 9, 26, 4, 30, tzinfo=timezone.utc)  # 07:30 Cairo, 00:30 New York
    assert is_due(cairo, now) and not is_due(ny, now)
    cairo.last_sent = date(2026, 9, 26)
    assert not is_due(cairo, now)  # never sends twice in one day


def test_scheduler_handles_daylight_saving():
    ny = User(2, "B", "America/New_York")
    assert is_due(ny, datetime(2026, 7, 1, 11, 0, tzinfo=timezone.utc))      # 07:00 EDT
    assert not is_due(ny, datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc))  # 06:00 EST
    assert is_due(ny, datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc))      # 07:00 EST
