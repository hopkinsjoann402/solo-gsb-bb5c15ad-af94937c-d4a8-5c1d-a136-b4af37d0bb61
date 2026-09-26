"""无线麦克风频点协调 API。"""

from fastapi import FastAPI

from .models import Assignment, CoordinateRequest, CoordinateResponse
from .solver import solve

app = FastAPI(
    title="无线麦克风频点协调 API",
    description=(
        "为最多 8 支无线麦克风从各自候选频点中各选一个，"
        "满足两两频差与三阶互调（|2fi−fj−fk|）均不小于保护间隔；"
        "优先减少有原频点麦克风的换频数量，再取频点数组字典序最小的全局最优解。"
    ),
    version="1.0.0",
)


@app.get("/health", tags=["meta"], summary="健康检查")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/v1/coordinate",
    response_model=CoordinateResponse,
    tags=["coordinate"],
    summary="求解全局最优频点分配方案",
)
def coordinate(req: CoordinateRequest) -> CoordinateResponse:
    mics = req.microphones
    result = solve(
        candidates=[m.candidates for m in mics],
        originals=[m.original for m in mics],
        guard=req.guard_interval,
    )
    if result is None:
        return CoordinateResponse(
            feasible=False,
            changed_count=0,
            assignments=[],
            message="无解：在给定候选频点与保护间隔下，不存在满足全部约束的分配方案",
        )

    assignments = [
        Assignment(
            id=m.id,
            frequency=f,
            changed=m.original is not None and f != m.original,
        )
        for m, f in zip(mics, result)
    ]
    changed_count = sum(1 for a in assignments if a.changed)
    return CoordinateResponse(
        feasible=True,
        changed_count=changed_count,
        assignments=assignments,
        message=f"求解成功：共 {changed_count} 支有原频点的麦克风需要换频",
    )
