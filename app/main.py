import json
import os
import secrets
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

try:
    from google import genai
except ImportError:  # pragma: no cover - allows startup without the SDK
    genai = None


load_dotenv()

DEFAULT_GEMINI_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
)


@dataclass
class Campaign:
    title: str
    story: str
    file_year: int
    security_level: str
    alias: str
    role: str
    token: str
    core_id: str
    clues: dict[int, str]


@dataclass
class GameState:
    mission: int = 1
    won: bool = False


game_state = GameState()


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str
    role: str


class FirewallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str
    security_token: str


def local_campaign() -> Campaign:
    suffix = secrets.token_hex(2).upper()
    campaign = Campaign(
        title=f"Operation {secrets.choice(['Blackout', 'Nightfall', 'Cipher', 'Redline'])}",
        story="An enemy control system is hiding its core behind four REST security layers.",
        file_year=secrets.choice([2023, 2024, 2025, 2026]),
        security_level=secrets.choice(["critical", "classified", "omega", "restricted"]),
        alias=secrets.choice(["Shadow", "Raven", "Specter", "Cipher"]),
        role="Hacker",
        token=f"TKN-{suffix}",
        core_id=f"NUC-{secrets.choice(['Omega', 'Astra', 'Vega', 'Nova'])}",
        clues={},
    )
    campaign.clues = build_explicit_clues(campaign)
    return campaign


def build_explicit_clues(campaign: Campaign) -> dict[int, str]:
    return {
        1: (
            f"Mission 1: The archive is read-only. Find the files resource and filter it with "
            f"two query keys: level and year. The security value is '{campaign.security_level}', "
            f"and the year is {campaign.file_year}. "
            "Do not send a request body."
        ),
        2: (
            f"Mission 2: The gate accepts a new access record. Create it with the write method "
            f"and a JSON body containing two fields. The alias is '{campaign.alias}'; the role is "
            f"'{campaign.role}'. The field names are ordinary English nouns."
        ),
        3: (
            f"Mission 3: The firewall is not destroyed; change only its state. Use the partial-update "
            f"method and prove your access with the token '{campaign.token}'. Set the state to the "
            "word that means disconnected."
        ),
        4: (
            f"Mission 4: The exposed core must disappear. Target the cores collection directly, "
            f"placing its identifier '{campaign.core_id}' in the address rather than in a body. "
            "Use the destructive HTTP method."
        ),
    }


def campaign_from_data(data: dict[str, Any]) -> Campaign:
    campaign = Campaign(
        title=str(data["title"]),
        story=str(data["story"]),
        file_year=int(data["file_year"]),
        security_level=str(data["security_level"]),
        alias=str(data["alias"]),
        role=str(data["role"]),
        token=str(data["token"]),
        core_id=str(data["core_id"]),
        clues={int(key): str(value) for key, value in data["clues"].items()},
    )
    if set(campaign.clues) != {1, 2, 3, 4}:
        raise ValueError("Campaign must contain four clues")
    return campaign


def generate_campaign() -> tuple[Campaign, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        campaign = local_campaign()
        return campaign, "local_mode"

    prompt = """Create one educational REST escape-room campaign as valid JSON only.
It must contain exactly four sequential missions:
1) GET /api/files with query parameters level and year.
2) POST /api/accesses with JSON body alias and role.
3) PATCH /api/firewall with JSON body state (the value must always be exactly
   the string 'offline') and security_token.
4) DELETE /api/cores/{core_id} with a path variable.
Any field with a fixed, single valid value (such as state) must always resolve
to that exact value, but you may still phrase the clue as an indirect riddle
around it.
Use exactly these JSON keys: title, story, file_year, security_level, alias, role, token, core_id, clues.
clues must be an object with string keys 1, 2, 3, 4. Each clue must be a different short
enemy-AI riddle, not a reusable template. It must describe the REST concept and provide enough
indirect information to solve the mission, but must not give the complete copy-paste request,
full URL with query string, or complete JSON body. It must still mention the correct HTTP method
and route, and may reveal individual values as puzzle hints. Never say that a later mission is
complete before its own request is made. Use safe fictional values only. Do not include markdown,
API keys, or extra keys."""

    configured_models = os.getenv("GEMINI_MODEL", "")
    models = tuple(model.strip() for model in configured_models.split(",") if model.strip())
    models = models or DEFAULT_GEMINI_MODELS
    client = genai.Client(api_key=api_key)

    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            response_text = (response.text or "").strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            campaign = campaign_from_data(json.loads(response_text))
            return campaign, model
        except (Exception, KeyError, TypeError, ValueError):
            continue

    campaign = local_campaign()
    return campaign, "local_mode"


campaign, campaign_source = generate_campaign()


app = FastAPI(
    title="REST Escape Room",
    description="Educational API for practicing HTTP methods, URIs, queries, bodies, and paths.",
    version="2.0.0",
)


def next_mission(mission: int) -> dict[str, Any] | None:
    if mission == 2:
        return {
            "mission": 2,
            "clue_endpoint": "GET /api/missions/2",
            "objective": "Create a new access resource with the required JSON body.",
        }
    if mission == 3:
        return {
            "mission": 3,
            "clue_endpoint": "GET /api/missions/3",
            "objective": "Partially update the firewall and set its state to offline.",
        }
    if mission == 4:
        return {
            "mission": 4,
            "clue_endpoint": "GET /api/missions/4",
            "objective": "Delete the exposed core using its path variable.",
        }
    return None


@app.get("/")
def welcome() -> dict[str, Any]:
    return {
        "message": "Welcome to the REST Escape Room.",
        "campaign": campaign.title,
        "story": campaign.story,
        "instructions": "Start by requesting mission 1.",
        "first_request": "GET /api/missions/1",
        "documentation": "/docs",
    }


@app.get("/api/missions/{mission_number}")
def get_mission(mission_number: int) -> dict[str, Any]:
    if mission_number not in (1, 2, 3, 4):
        raise HTTPException(status_code=404, detail="That mission does not exist.")

    if mission_number != game_state.mission:
        raise HTTPException(status_code=409, detail=f"Your current mission is {game_state.mission}.")

    return {
        "mission": mission_number,
        "campaign": campaign.title,
        "clue": campaign.clues[mission_number],
        "generated_by": campaign_source,
    }


@app.get("/api/files")
def inspect_files(
    request: Request,
    level: str | None = Query(default=None),
    year: int | None = Query(default=None),
) -> JSONResponse:
    query_items = list(request.query_params.multi_items())
    exact_query = len(query_items) == 2 and dict(query_items) == {
        "level": campaign.security_level,
        "year": str(campaign.file_year),
    }
    if not exact_query or level != campaign.security_level or year != campaign.file_year:
        raise HTTPException(status_code=400, detail="Use exactly the values requested by mission 1.")

    if game_state.mission != 1:
        raise HTTPException(status_code=409, detail=f"Your current mission is {game_state.mission}.")
    game_state.mission = 2
    return JSONResponse(
        status_code=200,
        content={"message": "Classified file found.", "next_mission": next_mission(2)},
    )


@app.post("/api/accesses", status_code=status.HTTP_201_CREATED)
def open_access(data: AccessRequest) -> dict[str, Any]:
    if data.alias != campaign.alias or data.role != campaign.role:
        raise HTTPException(status_code=403, detail="The alias or role is incorrect.")

    if game_state.mission != 2:
        raise HTTPException(status_code=409, detail=f"Your current mission is {game_state.mission}.")
    game_state.mission = 3
    return {"message": "Access granted.", "security_token": campaign.token, "next_mission": next_mission(3)}


@app.patch("/api/firewall")
def update_firewall(data: FirewallRequest) -> dict[str, Any]:
    if data.state != "offline" or data.security_token != campaign.token:
        raise HTTPException(status_code=403, detail="The firewall state or token is incorrect.")

    if game_state.mission != 3:
        raise HTTPException(status_code=409, detail=f"Your current mission is {game_state.mission}.")
    game_state.mission = 4
    return {"message": f"Firewall breached. Core {campaign.core_id} is exposed.", "next_mission": next_mission(4)}


@app.delete("/api/cores/{core_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy_core(core_id: str) -> None:
    if game_state.mission != 4:
        raise HTTPException(status_code=409, detail=f"Your current mission is {game_state.mission}.")
    if core_id != campaign.core_id:
        raise HTTPException(status_code=404, detail="Core not found.")

    game_state.won = True
    game_state.mission = 5
    return None


@app.get("/api/status")
def game_status() -> dict[str, Any]:
    return {"current_mission": game_state.mission, "won": game_state.won, "campaign": campaign.title}
