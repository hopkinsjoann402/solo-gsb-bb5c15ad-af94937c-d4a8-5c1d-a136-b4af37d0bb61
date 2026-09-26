"""演出无线麦克风频点协调 API。"""
from __future__ import annotations

from fastapi import FastAPI

from .models import Assignment, CoordinateRequest, CoordinateResponse
from .solver import solve

app = FastAPI(
    title="无线麦克风频点协调 API",
    description=(
        "为最多 8 支演出无线麦克风从各自候选频点中选择最终频点：\n\n"
        "- 任意两支频差不小于保护间隔；\n"
        "- 任意三支不同麦克风的所有有序组合均满足 |2fi−fj−fk| 不小于保护间隔；\n"
        "- 全局最优：优先最少换频（有原频点的麦克风），再按输入顺序取频点数组字典序最小。"
    ),
    version="1.0.0",
)


@app.get("/", summary="服务信息")
def root() -> dict:
    return {
        "service": "wireless-mic-frequency-coordinator",
        "docs": "/docs",
        "coordinate": "POST /api/v1/coordinate",
    }


@app.get("/health", summary="健康检查")
def health() -> dict:
    return {"status": "healthy"}


@app.post(
    "/api/v1/coordinate",
    response_model=CoordinateResponse,
    summary="频点协调求解",
    response_description="status=ok 时返回最优方案；status=no_solution 时明确返回无解",
)
def coordinate(req: CoordinateRequest) -> CoordinateResponse:
    result = solve(
        candidates=[m.candidates for m in req.microphones],
        originals=[m.original for m in req.microphones],
        guard=req.guard_interval,
    )

    if not result.feasible:
        return CoordinateResponse(
            status="no_solution",
            guard_interval=req.guard_interval,
            checked_triples=result.checked_triples,
            detail=(
                "在给定的候选频点与保护间隔下，不存在同时满足两两频差约束和"
                "三频互调约束 |2fi−fj−fk|≥g 的方案；请扩大候选频点或减小保护间隔。"
            ),
        )

    assignments = []
    for i, (mic, freq) in enumerate(zip(req.microphones, result.frequencies)):
        assignments.append(
            Assignment(
                id=mic.id or f"mic-{i + 1}",
                frequency=freq,
                original=mic.original,
                changed=mic.original is not None and freq != mic.original,
            )
        )

    return CoordinateResponse(
        status="ok",
        guard_interval=req.guard_interval,
        changed_count=result.changed_count,
        frequencies=result.frequencies,
        assignments=assignments,
        checked_triples=result.checked_triples,
        detail=None,
    )
