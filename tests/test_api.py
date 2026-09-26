"""API 集成测试。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "coordinate" in r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_coordinate_ok():
    payload = {
        "guard_interval": 200,
        "microphones": [
            {"id": "lead-vocal", "candidates": [600100, 600400, 600900], "original": 600400},
            {"id": "backing-1", "candidates": [601000, 601300, 601600], "original": 601300},
            {"id": "backing-2", "candidates": [602000, 602300, 602600]},
        ],
    }
    r = client.post("/api/v1/coordinate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["changed_count"] == 0
    assert body["frequencies"] == [600400, 601300, 602000]
    assert len(body["assignments"]) == 3
    assert body["assignments"][0]["id"] == "lead-vocal"
    assert body["assignments"][0]["changed"] is False


def test_coordinate_default_ids():
    payload = {
        "guard_interval": 100,
        "microphones": [
            {"candidates": [500, 900]},
            {"candidates": [700, 1200]},
        ],
    }
    r = client.post("/api/v1/coordinate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert [a["id"] for a in body["assignments"]] == ["mic-1", "mic-2"]
    assert body["frequencies"] == [500, 700]


def test_coordinate_no_solution():
    payload = {
        "guard_interval": 1000,
        "microphones": [
            {"candidates": [100]},
            {"candidates": [200]},
        ],
    }
    r = client.post("/api/v1/coordinate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_solution"
    assert body["frequencies"] is None
    assert body["assignments"] is None
    assert body["detail"]


def test_coordinate_intermod_no_solution():
    # 两两频差满足，但三频互调约束不满足
    payload = {
        "guard_interval": 100,
        "microphones": [
            {"candidates": [500]},
            {"candidates": [600]},
            {"candidates": [750]},
        ],
    }
    r = client.post("/api/v1/coordinate", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "no_solution"


@pytest.mark.parametrize(
    "payload",
    [
        # 保护间隔必须为正整数
        {"guard_interval": 0, "microphones": [{"candidates": [100]}]},
        {"guard_interval": -5, "microphones": [{"candidates": [100]}]},
        # 麦克风数量 1~8
        {"guard_interval": 10, "microphones": []},
        {
            "guard_interval": 10,
            "microphones": [{"candidates": [100 + i * 1000]} for i in range(9)],
        },
        # 候选频点 1~6 个
        {"guard_interval": 10, "microphones": [{"candidates": []}]},
        {"guard_interval": 10, "microphones": [{"candidates": [1, 2, 3, 4, 5, 6, 7]}]},
        # 频点必须为非负整数
        {"guard_interval": 10, "microphones": [{"candidates": [-100]}]},
        {"guard_interval": 10, "microphones": [{"candidates": [100.5]}]},
        # id 必须唯一
        {
            "guard_interval": 10,
            "microphones": [
                {"id": "a", "candidates": [100]},
                {"id": "a", "candidates": [200]},
            ],
        },
        # 缺字段 / 类型错误
        {"microphones": [{"candidates": [100]}]},
        {"guard_interval": "abc", "microphones": [{"candidates": [100]}]},
    ],
)
def test_coordinate_validation_errors(payload):
    r = client.post("/api/v1/coordinate", json=payload)
    assert r.status_code == 422
    assert r.json()["detail"]
