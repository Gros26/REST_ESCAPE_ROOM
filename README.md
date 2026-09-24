# REST Escape Room

Educational API built with Python and FastAPI. Players practice HTTP methods, URIs, query parameters, JSON bodies, and path variables through a four-mission sequence.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for the welcome message or `http://127.0.0.1:8000/docs` for interactive API documentation.

## Dynamic campaigns

Every server restart creates a new campaign. If `GEMINI_API_KEY` is configured, Gemini generates the campaign story, values, and explicit English clues. The default model is `gemini-3.6-flash`; the application automatically tries other configured free-tier models if needed. Set `GEMINI_MODEL` in `.env` to override it, or provide a comma-separated list such as `gemini-3.6-flash,gemini-3.5-flash-lite`.

Gemini only creates the narrative and challenge values. The backend validates every value and controls the mission sequence, so an AI response cannot bypass a mission.

## Stateless game flow

The API is stateless: the server stores no game progress. Every request carries the team's progress in the `X-Game-State` header as an HMAC-signed token returned by the previous response. Send no header to start a fresh game (mission 1), and copy the `X-Game-State` value from each response into the next request:

```bash
# 1. Request the first mission clue (no header -> fresh game)
curl -i http://127.0.0.1:8000/api/missions/1
# Copy the X-Game-State value from the response headers into <state-1>

# 2. Solve mission 1 using the level and year shown in its clue
curl -i -H "X-Game-State: <state-1>" \
  "http://127.0.0.1:8000/api/files?level=critical&year=2025"
# The X-Game-State header of this response advances the game to mission 2

# 3. Request mission 2, then use the alias and role shown in its clue.
curl -i -H "X-Game-State: <state-2>" \
  http://127.0.0.1:8000/api/missions/2

curl -i -X POST -H "Content-Type: application/json" \
  -H "X-Game-State: <state-2>" \
  -d '{"alias":"Shadow","role":"Hacker"}' \
  http://127.0.0.1:8000/api/accesses

# 4. Request mission 3, then use its token in the PATCH body.
curl -i -H "X-Game-State: <state-3>" \
  http://127.0.0.1:8000/api/missions/3

curl -i -X PATCH -H "Content-Type: application/json" \
  -H "X-Game-State: <state-3>" \
  -d '{"state":"offline","security_token":"TKN-AB12"}' \
  http://127.0.0.1:8000/api/firewall

# 5. Request mission 4, then delete the core ID shown in its clue.
curl -i -H "X-Game-State: <state-4>" \
  http://127.0.0.1:8000/api/missions/4

curl -i -X DELETE -H "X-Game-State: <state-4>" \
  http://127.0.0.1:8000/api/cores/NUC-Omega
```

The values in this example are illustrative. Always use the values from the current campaign's clues because they change after a restart.

`GET /api/status` reads the team's progress from the same `X-Game-State` header. The token is HMAC-signed with `GAME_SIGNING_SECRET` (a fresh random value each process, overridable in `.env`), so players cannot forge or skip missions. If the team loses its token, the progress is lost — the server does not remember it. Restarting the server keeps the same rules but creates a new campaign.

## Tests

```bash
.venv/bin/python -m pytest -q
```
