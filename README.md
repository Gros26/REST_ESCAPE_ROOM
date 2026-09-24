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

## Sequential game flow

The server keeps one game state in memory. After each successful mission, the response includes `next_mission`. Then request that mission's clue before solving it:

```bash
# 1. Request the first explicit mission
curl http://127.0.0.1:8000/api/missions/1

# 2. Solve mission 1 using the level and year shown in its clue
curl "http://127.0.0.1:8000/api/files?level=critical&year=2025"

# 3. Request mission 2. Use the alias and role shown in its clue.
curl http://127.0.0.1:8000/api/missions/2

curl -X POST -H "Content-Type: application/json" \
  -d '{"alias":"Shadow","role":"Hacker"}' \
  http://127.0.0.1:8000/api/accesses

# 4. Request mission 3, then use its token in the PATCH body.
curl http://127.0.0.1:8000/api/missions/3

curl -X PATCH -H "Content-Type: application/json" \
  -d '{"state":"offline","security_token":"TKN-AB12"}' \
  http://127.0.0.1:8000/api/firewall

# 5. Request mission 4, then delete the core ID shown in its clue.
curl http://127.0.0.1:8000/api/missions/4

curl -i -X DELETE http://127.0.0.1:8000/api/cores/NUC-Omega
```

The values in this example are illustrative. Always use the values from the current campaign's clues because they change after a restart.

`GET /api/status` shows the current mission. State is held in memory, so restarting the server resets progress and creates a new campaign.

## Tests

```bash
.venv/bin/python -m pytest -q
```
