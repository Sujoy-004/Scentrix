"""Adaptive quiz session endpoint tests (in-memory store)."""


def test_start_returns_session_id_and_seed_questions(client):
    resp = client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 6, "candidate_pool_size": 200},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session_id"]
    assert len(data["seed_questions"]) == 6
    assert data["seed_questions"][0]["fragrance_id"]


def test_answer_then_guest_finalize(client):
    start = client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 6, "candidate_pool_size": 200},
    ).json()["data"]
    session_id = start["session_id"]
    fid = start["seed_questions"][0]["fragrance_id"]

    answer = client.post(
        f"/fragrances/quiz/session/{session_id}/answer",
        json={"fragrance_id": fid, "rating_1_to_10": 8, "source": "quiz_core"},
    )
    assert answer.status_code == 200
    a_data = answer.json()["data"]
    assert a_data["accepted"] is True
    assert a_data["answers_count"] == 1

    finalize = client.post(f"/fragrances/quiz/session/{session_id}/guest-finalize")
    assert finalize.status_code == 200
    assert finalize.json()["data"]["message"] == "Guest quiz finalized"