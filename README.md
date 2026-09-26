# AI Daily Horoscope – Demo

A working core for a personalized AI horoscope service. It takes a user's birth data, calculates their natal chart and today's planetary transits with the Swiss Ephemeris (`pyswisseph`), finds the transits that hit their chart most exactly, and sends that data to GPT-4o mini or Claude to write the horoscope.

```
birth data ──► natal chart (planets, ascendant, houses)
                     │
today's sky ──► transit-to-natal aspects (tightest first)
                     │
                     ▼
         structured prompt ──► OpenAI / Anthropic ──► horoscope text
```

## What it does

- **Natal chart**: positions of the Sun through Pluto, retrograde flags, Ascendant and Placidus house cusps (falls back to whole-sign houses at polar latitudes). Uses the built-in Moshier ephemeris, so no data files are needed.
- **Transits**: the sky at 07:00 in the user's own time zone on the horoscope date.
- **Aspects**: conjunction, sextile, square, trine and opposition, with a 3° orb (5° for the fast-moving Moon), sorted by exactness, plus the natal house each transit falls in.
- **Prompt engineering**: a fixed system prompt (tone, length, structure, safety rules) and a data-only user prompt, so the model interprets real placements instead of inventing them.
- **Two providers**: `--provider openai` (GPT-4o mini) or `--provider anthropic` (Claude), switchable per request.
- **Scheduling logic** (`scheduler.py`): an hourly job picks the users whose local time has passed 07:00 and who have not received today's horoscope. This handles every time zone and daylight saving, and never double-sends on a retry.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # add your OpenAI or Anthropic key

# By city (geocoded to lat/lon and time zone)
python main.py --name Sara --date 1995-04-12 --time 08:30 --city "Tanta, Egypt"

# Or with explicit coordinates, using Claude
python main.py --name Sara --date 1995-04-12 --time 08:30 \
  --lat 30.79 --lon 31.00 --tz Africa/Cairo --provider anthropic

# See the chart data and prompt without calling the LLM
python main.py --name Sara --date 1995-04-12 --time 08:30 --city "Tanta, Egypt" --dry-run
```

## Tests

```bash
pytest -q
```

The tests cover aspect detection (including the 0° Aries wraparound), house placement, prompt building, and delivery timing across time zones and daylight-saving changes.

## Project layout

| File | Purpose |
|------|---------|
| `astro.py` | Natal chart, transits, aspects, houses |
| `prompts.py` | System prompt and user prompt builder |
| `llm.py` | OpenAI / Anthropic calls |
| `scheduler.py` | Which users are due for delivery right now |
| `main.py` | Command-line entry point |

## From demo to product

In the full MVP, this core sits behind a FastAPI backend. User birth data and time zone are stored in PostgreSQL, Lemon Squeezy webhooks activate or cancel subscriptions, and a Celery beat job runs `users_due()` every hour. Each due user gets a task that generates the horoscope and delivers it by email (Resend) or Telegram bot.
