# REST Escape Room

Educational API built with Python and FastAPI. Players practice HTTP methods, URIs, query parameters, body parameters, and path variables while completing three levels.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

`GEMINI_API_KEY` is optional. Without it, the game uses local clues. With it, `GET /api/clues/{level}` generates clues with `gemini-2.5-flash`. The API key is never returned to the client.

## Game flow

Use the same `X-Session-ID` header for every request so the server can preserve a team's progress. Two people in different locations can share progress by using the same ID and connecting to the same public server:

```bash
export SESSION=team-1

# Request the current level's clue
curl -H "X-Session-ID: $SESSION" http://127.0.0.1:8000/api/clues/1

# Level 1: exact query parameters
curl -H "X-Session-ID: $SESSION" \
  "http://127.0.0.1:8000/api/files?level=top_secret&year=2024"

# Level 2: JSON body and POST method
curl -i -X POST -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION" \
  -d '{"access_type":"digital_fingerprint","key":"KEY-ORBIT-2024"}' \
  http://127.0.0.1:8000/api/accesses

# Level 3: path variable and DELETE method
curl -i -X DELETE -H "X-Session-ID: $SESSION" \
  http://127.0.0.1:8000/api/drones/DRN-808
```

The `GET /api/status` route shows the current progress. State is kept in memory for classroom simplicity; restarting the server resets all games. This means the shared session works across distant clients while this same server process is running, but it is not yet persistent across restarts or multiple server instances.

## Extending the game

To add a level, add its local clue and prompt in `generate_clue`, add a route that validates the new REST concept, and update `GameState.level` when the challenge is completed. Gemini does not control security state; it only writes the clue. This separation prevents an unpredictable AI response from skipping levels.

## Tests

```bash
.venv/bin/python -m pytest -q
```
