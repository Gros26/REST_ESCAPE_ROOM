from fastapi.testclient import TestClient

from app.main import app, campaign, game_state


client = TestClient(app)


def setup_function() -> None:
    game_state.mission = 1
    game_state.won = False


def test_root_welcomes_players() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["first_request"] == "GET /api/missions/1"
    assert response.json()["documentation"] == "/docs"


def test_full_winning_path() -> None:
    clue = client.get("/api/missions/1")
    assert clue.status_code == 200
    assert clue.json()["clue"]
    assert clue.json()["generated_by"]

    files = client.get(
        f"/api/files?level={campaign.security_level}&year={campaign.file_year}",
    )
    assert files.status_code == 200
    assert files.json()["next_mission"]["mission"] == 2

    access = client.post(
        "/api/accesses",
        json={"alias": campaign.alias, "role": campaign.role},
    )
    assert access.status_code == 201

    firewall = client.patch(
        "/api/firewall",
        json={"state": "offline", "security_token": campaign.token},
    )
    assert firewall.status_code == 200

    destroyed = client.delete(f"/api/cores/{campaign.core_id}")
    assert destroyed.status_code == 204
    assert client.get("/api/status").json()["won"] is True


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
