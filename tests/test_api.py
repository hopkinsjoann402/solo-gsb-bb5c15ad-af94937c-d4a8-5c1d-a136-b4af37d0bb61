"""API 接口测试。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PAYLOAD = {
    "guard_interval": 100,
    "microphones": [
        {"id": "mic-1", "candidates": [470000, 470200, 470400], "original": 470000},
        {"id": "mic-2", "candidates": [470100, 470300, 470500], "original": 470100},
        {"id": "mic-3", "candidates": [470600, 470800, 471000]},
    ],
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_coordinate_feasible():
    resp = client.post("/api/v1/coordinate", json=PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feasible"] is True
    assert [a["id"] for a in body["assignments"]] == ["mic-1", "mic-2", "mic-3"]
    freqs = [a["frequency"] for a in body["assignments"]]
    guard = PAYLOAD["guard_interval"]
    for i in range(len(freqs)):
        for j in range(len(freqs)):
            if i != j:
                assert abs(freqs[i] - freqs[j]) >= guard
    assert body["changed_count"] == sum(a["changed"] for a in body["assignments"])


def test_coordinate_prefers_keeping_originals():
    resp = client.post("/api/v1/coordinate", json=PAYLOAD)
    body = resp.json()
    # 该用例存在两支都保持原频点的可行解
    assert body["changed_count"] == 0
    assert body["assignments"][0]["frequency"] == 470000


def test_coordinate_infeasible():
    payload = {
        "guard_interval": 500,
        "microphones": [
            {"id": "a", "candidates": [100, 200]},
            {"id": "b", "candidates": [150, 250]},
        ],
    }
    resp = client.post("/api/v1/coordinate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feasible"] is False
    assert body["assignments"] == []
    assert "无解" in body["message"]


def test_validation_too_many_microphones():
    payload = {
        "guard_interval": 10,
        "microphones": [{"id": f"m{i}", "candidates": [100]} for i in range(9)],
    }
    assert client.post("/api/v1/coordinate", json=payload).status_code == 422


def test_validation_too_many_candidates():
    payload = {
        "guard_interval": 10,
        "microphones": [{"id": "a", "candidates": [1, 2, 3, 4, 5, 6, 7]}],
    }
    assert client.post("/api/v1/coordinate", json=payload).status_code == 422


def test_validation_guard_interval_must_be_positive():
    payload = {
        "guard_interval": 0,
        "microphones": [{"id": "a", "candidates": [100]}],
    }
    assert client.post("/api/v1/coordinate", json=payload).status_code == 422


def test_validation_duplicate_microphone_ids():
    payload = {
        "guard_interval": 10,
        "microphones": [
            {"id": "a", "candidates": [100]},
            {"id": "a", "candidates": [200]},
        ],
    }
    assert client.post("/api/v1/coordinate", json=payload).status_code == 422


def test_validation_non_positive_candidate():
    payload = {
        "guard_interval": 10,
        "microphones": [{"id": "a", "candidates": [0, 100]}],
    }
    assert client.post("/api/v1/coordinate", json=payload).status_code == 422
