from fastapi.testclient import TestClient

from app.main import app, campaign


client = TestClient(app)


def game_state(response) -> dict[str, str]:
    return {"X-Game-State": response.headers["X-Game-State"]}


def test_root_welcomes_players() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["first_request"] == "GET /api/missions/1"
    assert response.json()["documentation"] == "/docs"
    assert response.json()["game_state_header"] == "X-Game-State"


def test_full_winning_path() -> None:
    clue = client.get("/api/missions/1")
    assert clue.status_code == 200
    assert clue.json()["clue"]
    assert clue.json()["generated_by"]

    files = client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}",
        headers=game_state(clue),
    )
    assert files.status_code == 200
    assert files.json()["next_mission"]["mission"] == 2

    access = client.post(
        "/api/accesses",
        json={"alias": campaign.alias, "role": campaign.role},
        headers=game_state(files),
    )
    assert access.status_code == 201
    assert access.headers["X-Game-State"]

    firewall = client.patch(
        "/api/firewall",
        json={"state": "offline", "security_token": campaign.token},
        headers=game_state(access),
    )
    assert firewall.status_code == 200

    destroyed = client.delete(
        f"/api/cores/{campaign.core_id}",
        headers=game_state(firewall),
    )
    assert destroyed.status_code == 204

    final_state = game_state(destroyed)
    status = client.get("/api/status", headers=final_state)
    assert status.json()["won"] is True


def test_state_travels_in_the_request_not_on_the_server() -> None:
    first = client.get("/api/files", params={
        "level": campaign.security_level,
        "year": campaign.file_year,
    })
    assert first.status_code == 200

    second = client.get("/api/files", params={
        "level": campaign.security_level,
        "year": campaign.file_year,
    })
    assert second.status_code == 200
    assert second.headers["X-Game-State"] == first.headers["X-Game-State"]


def test_forged_state_token_is_rejected() -> None:
    clue = client.get("/api/missions/1")
    forged = clue.headers.get("X-Game-State", "")
    payload, _ = forged.split(".")
    response = client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}",
        headers={"X-Game-State": f"{payload}.forgedsignature"},
    )
    assert response.status_code == 400


def test_mission_out_of_order_returns_conflict() -> None:
    clue = client.get("/api/missions/1")
    solved = client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}",
        headers=game_state(clue),
    )
    assert solved.status_code == 200

    again = client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}",
        headers=game_state(solved),
    )
    assert again.status_code == 409


def test_files_requires_exact_query_parameters() -> None:
    assert client.get(f"/api/files?level={campaign.security_level}").status_code == 400
    assert client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}&debug=true"
    ).status_code == 400


def test_access_rejects_wrong_body() -> None:
    response = client.post(
        "/api/accesses",
        json={"alias": "incorrect", "role": campaign.role},
    )
    assert response.status_code == 403


def test_core_id_is_a_path_variable() -> None:
    assert client.delete("/api/cores/NUC-404").status_code == 409
