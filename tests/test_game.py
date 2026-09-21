from fastapi.testclient import TestClient

from app.main import ACCESS_KEY, app, sessions


client = TestClient(app)


def setup_function() -> None:
    sessions.clear()


def test_root_welcomes_players() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["first_request"] == "GET /api/clues/1"
    assert response.json()["documentation"] == "/docs"


def test_full_winning_path() -> None:
    headers = {"X-Session-ID": "team-1"}

    clue = client.get("/api/clues/1", headers=headers)
    assert clue.status_code == 200

    files = client.get("/api/files?level=top_secret&year=2024", headers=headers)
    assert files.status_code == 200
    assert files.json()["access_key"] == ACCESS_KEY

    access = client.post(
        "/api/accesses",
        headers=headers,
        json={"access_type": "digital_fingerprint", "key": ACCESS_KEY},
    )
    assert access.status_code == 201

    destroyed = client.delete("/api/drones/DRN-808", headers=headers)
    assert destroyed.status_code == 204
    assert client.get("/api/status", headers=headers).json() == {"current_level": 4, "won": True}


def test_files_requires_exact_query_parameters() -> None:
    assert client.get("/api/files?level=top_secret").status_code == 400
    assert client.get("/api/files?level=top_secret&year=2024&debug=true").status_code == 400


def test_access_rejects_wrong_body() -> None:
    response = client.post(
        "/api/accesses",
        json={"access_type": "digital_fingerprint", "key": "incorrect"},
    )
    assert response.status_code == 403


def test_drone_id_is_a_path_variable() -> None:
    assert client.delete("/api/drones/DRN-404").status_code == 404
