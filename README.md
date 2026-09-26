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

## Sample run

Real output for a test user born 12 April 1995, 08:30, in Tanta, Egypt, with the horoscope generated for 26 September 2026:

```
Reader: Sara
Date: Saturday, 26 September 2026
Natal chart: Sun in Aries, Moon in Virgo, rising sign Gemini.

Today's sky:
- Sun 3° Libra
- Moon 26° Pisces
- Mercury 24° Libra
- Venus 8° Scorpio
- Mars 29° Cancer
- Jupiter 19° Leo
- Saturn 12° Aries (retrograde)
- Uranus 6° Gemini (retrograde)
- Neptune 3° Aries (retrograde)
- Pluto 3° Aquarius (retrograde)

Most exact transits to the natal chart today (tightest first):
- Transiting Jupiter 19° Leo trine natal Mercury 19° Aries (orb 0.7°, in your natal house 3)
- Transiting Moon 26° Pisces sextile natal Neptune 25° Capricorn (orb 0.9°, in your natal house 10)
- Transiting Mars 29° Cancer trine natal Pluto 0° Sagittarius (retrograde) (orb 1.3°, in your natal house 2)
- Transiting Mars 29° Cancer opposition natal Uranus 0° Aquarius (orb 1.4°, in your natal house 2)
- Transiting Mercury 24° Libra square natal Neptune 25° Capricorn (orb 1.4°, in your natal house 5)
```

Generated horoscope:

> Dear Sara, today brings a lively mix of energies, encouraging both connection and deep personal reflection.
>
> You'll find your mind is especially sharp and optimistic, making this a wonderful day for conversations and sharing your ideas. There's a natural flow to expressing yourself, thanks to a harmonious *trine* aspect, which signifies ease and opportunity, allowing you to connect easily with others and perhaps discover new avenues for learning. Your intuition also feels heightened, offering inspiring insights, especially regarding your long-term goals or career direction. Trust those quiet nudges that guide you toward what truly resonates with your purpose.

The Jupiter–Mercury trine (orb 0.7°) becomes "your mind is especially sharp and optimistic… conversations and sharing your ideas", and the Moon–Neptune sextile in the 10th house becomes intuition about "career direction". Every line traces back to a real placement in her chart.

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

### Testing without a paid API key

The OpenAI client works with any OpenAI-compatible endpoint, so you can try the demo on a free tier by setting these in `.env`:

```bash
# Google Gemini (free key from aistudio.google.com)
OPENAI_API_KEY=your-gemini-key
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_MODEL=gemini-2.5-flash
LLM_REASONING_EFFORT=none

# or Groq (free key from console.groq.com)
OPENAI_API_KEY=your-groq-key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
```

The chart and transit calculation runs fully offline. `--dry-run` shows everything that is sent to the model.

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
