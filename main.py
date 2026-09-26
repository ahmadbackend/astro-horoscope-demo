"""Generate a personalized daily horoscope from real planetary positions.

Examples:
    python main.py --name Sara --date 1995-04-12 --time 08:30 --city "Tanta, Egypt"
    python main.py --name Sara --date 1995-04-12 --time 08:30 \\
        --lat 30.79 --lon 31.00 --tz Africa/Cairo --provider anthropic
    python main.py ... --dry-run      # print chart data and prompt, skip the LLM call
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    def load_dotenv() -> None:
        pass

from astro import find_aspects, natal_chart, transits_at
from llm import generate
from prompts import SYSTEM_PROMPT, build_user_prompt
from scheduler import DELIVERY_HOUR


def geocode(city: str) -> tuple[float, float, str]:
    """City name -> (lat, lon, IANA time zone)."""
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder

    location = Nominatim(user_agent="astro-horoscope-demo").geocode(city)
    if location is None:
        raise SystemExit(f"Could not find city: {city}")
    tz = TimezoneFinder().timezone_at(lat=location.latitude, lng=location.longitude)
    return location.latitude, location.longitude, tz


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--date", required=True, help="Birth date, YYYY-MM-DD")
    p.add_argument("--time", required=True, help="Birth time, HH:MM (local)")
    p.add_argument("--city", help="Birth city, e.g. 'Tanta, Egypt' (geocoded)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--tz", help="IANA time zone, e.g. Africa/Cairo")
    p.add_argument("--for-date", help="Horoscope date, YYYY-MM-DD (default: today)")
    p.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    p.add_argument("--dry-run", action="store_true", help="Print the prompt without calling the LLM")
    args = p.parse_args()

    if args.city:
        lat, lon, tz = geocode(args.city)
    elif None not in (args.lat, args.lon, args.tz):
        lat, lon, tz = args.lat, args.lon, args.tz
    else:
        p.error("give either --city or all of --lat, --lon and --tz")

    birth_date = date.fromisoformat(args.date)
    birth_time = time.fromisoformat(args.time)
    natal = natal_chart(birth_date, birth_time, tz, lat, lon)

    # Transits are taken at the user's local delivery time on the horoscope date.
    day = date.fromisoformat(args.for_date) if args.for_date else datetime.now(ZoneInfo(tz)).date()
    moment = datetime.combine(day, time(DELIVERY_HOUR), tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))
    transits = transits_at(moment)
    aspects = find_aspects(transits, natal)

    user_prompt = build_user_prompt(args.name, day, natal, transits, aspects)

    print("=" * 60)
    print(user_prompt)
    print("=" * 60)

    if args.dry_run:
        return

    print(f"\nGenerating with {args.provider}...\n")
    print(generate(SYSTEM_PROMPT, user_prompt, args.provider))


if __name__ == "__main__":
    main()
