"""请求 / 响应模型与校验规则。"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

MAX_MICROPHONES = 8
MAX_CANDIDATES = 6


class Microphone(BaseModel):
    """一支无线麦克风的频点诉求。"""

    id: str = Field(..., min_length=1, max_length=64, description="麦克风标识，须在请求内唯一")
    candidates: List[int] = Field(
        ..., min_length=1, max_length=MAX_CANDIDATES,
        description="候选频点（kHz，正整数），最多 6 个",
    )
    original: Optional[int] = Field(
        default=None, gt=0, description="原频点（kHz，可选）；选中等于原频点的候选则不计换频"
    )

    @field_validator("candidates")
    @classmethod
    def candidates_positive(cls, v: List[int]) -> List[int]:
        if any(f <= 0 for f in v):
            raise ValueError("候选频点必须为正整数（kHz）")
        return v


class CoordinateRequest(BaseModel):
    """频点协调请求。"""

    guard_interval: int = Field(..., gt=0, description="保护间隔（kHz，正整数）")
    microphones: List[Microphone] = Field(
        ..., min_length=1, max_length=MAX_MICROPHONES,
        description="麦克风列表，最多 8 支",
    )

    @field_validator("microphones")
    @classmethod
    def microphone_ids_unique(cls, v: List[Microphone]) -> List[Microphone]:
        ids = [m.id for m in v]
        if len(set(ids)) != len(ids):
            raise ValueError("麦克风 id 必须唯一")
        return v


class Assignment(BaseModel):
    """单支麦克风的分配结果。"""

    id: str
    frequency: int = Field(..., description="分配到的频点（kHz）")
    changed: bool = Field(..., description="相对原频点是否发生换频（无原频点恒为 false）")


class CoordinateResponse(BaseModel):
    """频点协调响应。"""

    feasible: bool = Field(..., description="是否存在满足全部约束的分配方案")
    changed_count: int = Field(default=0, description="有原频点且被换频的麦克风数量")
    assignments: List[Assignment] = Field(
        default_factory=list, description="按输入顺序的分配结果"
    )
    message: str = Field(default="", description="结果说明，无解时给出明确原因")
