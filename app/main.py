import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

try:
    from google import genai
except ImportError:  # pragma: no cover - allows startup without the SDK
    genai = None


load_dotenv()


ACCESS_KEY = os.getenv("LEVEL_1_ACCESS_KEY", "KEY-ORBIT-2024")
GEMINI_MODEL = "gemini-2.5-flash"


@dataclass
class GameState:
    level: int = 1
    won: bool = False


sessions: dict[str, GameState] = {}


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_type: str
    key: str


def get_game_state(session_id: str) -> GameState:
    return sessions.setdefault(session_id, GameState())


def local_clue(level: int) -> str:
    clues = {
        1: "Level 1: The terminal does not listen to the body. Find two values in the query: level and year.",
        2: "Level 2: The message now travels inside the body. Use POST and send access_type and key as JSON.",
        3: "Level 3: The final target is in the address itself. Delete the drone with ID DRN-808.",
    }
    return clues[level]


def generate_clue(level: int) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return local_clue(level)

    prompt = f"""Act as an enemy and sarcastic AI in an educational REST escape room.
Generate one brief, cryptic, student-friendly clue for level {level}.
The solution must point to that level's REST route, but do not reveal every value literally.
Level 1 validates query parameters in GET /api/files.
Level 2 validates body parameters in POST /api/accesses.
Level 3 validates the path variable in DELETE /api/drones/{{drone_id}}.
Do not use markdown, invent routes, or include the API key."""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (response.text or "").strip()
        return text or local_clue(level)
    except Exception:
        # Keep the game usable when Gemini is temporarily unavailable.
        return local_clue(level)


app = FastAPI(
    title="REST Escape Room",
    description="Educational API for practicing HTTP methods, URIs, queries, bodies, and paths.",
    version="1.0.0",
)


@app.get("/")
def welcome() -> dict[str, Any]:
    return {
        "message": "Welcome to the REST Escape Room.",
        "instructions": "Start by requesting the clue for level 1.",
        "first_request": "GET /api/clues/1",
        "session_header": "X-Session-ID: team-1",
        "documentation": "/docs",
        "available_routes": {
            "clues": "GET /api/clues/{level}",
            "files": "GET /api/files?level=top_secret&year=2024",
            "accesses": "POST /api/accesses",
            "drones": "DELETE /api/drones/{drone_id}",
            "status": "GET /api/status",
        },
    }


@app.get("/api/clues/{level}")
def get_clue(level: int, x_session_id: str = Header(default="demo")) -> dict[str, Any]:
    if level not in (1, 2, 3):
        raise HTTPException(status_code=404, detail="That level does not exist.")

    state = get_game_state(x_session_id)
    return {
        "level": level,
        "current_level": state.level,
        "clue": generate_clue(level),
        "generated_by": "gemini-2.5-flash" if os.getenv("GEMINI_API_KEY") and genai else "local_mode",
    }


@app.get("/api/files")
def inspect_files(
    request: Request,
    level: str | None = Query(default=None),
    year: int | None = Query(default=None),
    x_session_id: str = Header(default="demo"),
) -> JSONResponse:
    query_items = list(request.query_params.multi_items())
    exact_query = len(query_items) == 2 and dict(query_items) == {"level": "top_secret", "year": "2024"}
    if not exact_query or level != "top_secret" or year != 2024:
        raise HTTPException(
            status_code=400,
            detail="Exactly ?level=top_secret&year=2024 is required.",
        )

    state = get_game_state(x_session_id)
    state.level = max(state.level, 2)
    return JSONResponse(
        status_code=200,
        content={"message": "Classified file unlocked.", "access_key": ACCESS_KEY, "next_level": 2},
    )


@app.post("/api/accesses", status_code=status.HTTP_201_CREATED)
def open_access(data: AccessRequest, x_session_id: str = Header(default="demo")) -> dict[str, Any]:
    if data.access_type != "digital_fingerprint" or data.key != ACCESS_KEY:
        raise HTTPException(status_code=403, detail="Incorrect fingerprint or key.")

    state = get_game_state(x_session_id)
    state.level = max(state.level, 3)
    return {
        "message": "Access granted. The final target is in the drone route.",
        "next_level": 3,
        "next_method": "DELETE",
    }


@app.delete("/api/drones/{drone_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy_drone(drone_id: str, x_session_id: str = Header(default="demo")) -> None:
    if drone_id != "DRN-808":
        raise HTTPException(status_code=404, detail="Drone not found.")

    state = get_game_state(x_session_id)
    state.won = True
    state.level = 4
    return None


@app.get("/api/status")
def game_status(x_session_id: str = Header(default="demo")) -> dict[str, Any]:
    state = get_game_state(x_session_id)
    return {"current_level": state.level, "won": state.won}
