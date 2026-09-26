"""Pydantic 请求/响应模型与请求校验。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Microphone(BaseModel):
    """一支麦克风：候选频点列表 + 可选原频点。"""

    id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="可选麦克风标识；缺省时按输入顺序生成 mic-1, mic-2 ...",
    )
    candidates: List[int] = Field(
        min_length=1,
        max_length=6,
        description="候选频点（kHz 整数），1~6 个；服务端会去重并升序排序",
    )
    original: Optional[int] = Field(
        default=None,
        ge=0,
        description="可选原频点（kHz 整数），用于优先尽量少换频",
    )

    @model_validator(mode="after")
    def _validate(self) -> "Microphone":
        for f in self.candidates:
            if f < 0:
                raise ValueError("candidates 中的频点必须是非负整数")
        return self


class CoordinateRequest(BaseModel):
    """频点协调请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "guard_interval": 200,
                    "microphones": [
                        {
                            "id": "lead-vocal",
                            "candidates": [600100, 600400, 600900],
                            "original": 600400,
                        },
                        {
                            "id": "backing-1",
                            "candidates": [601000, 601300, 601600],
                            "original": 601300,
                        },
                        {
                            "id": "backing-2",
                            "candidates": [602000, 602300, 602600],
                        },
                    ],
                }
            ]
        }
    )

    guard_interval: int = Field(
        gt=0,
        description="保护间隔（kHz 正整数）",
        json_schema_extra={"examples": [200]},
    )
    microphones: List[Microphone] = Field(
        min_length=1,
        max_length=8,
        description="麦克风列表，1~8 支",
    )

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> "CoordinateRequest":
        ids = [m.id for m in self.microphones if m.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("microphones 中的 id 必须唯一")
        return self


class Assignment(BaseModel):
    """单支麦克风的最终选频结果。"""

    id: str
    frequency: int = Field(description="最终选定频点（kHz）")
    original: Optional[int] = Field(description="原频点（kHz），未提供时为 null")
    changed: bool = Field(
        description="该麦克风是否换频：提供了原频点且选定频点 != 原频点时为 true"
    )


class CoordinateResponse(BaseModel):
    status: str = Field(description="ok 表示找到方案；no_solution 表示无解")
    guard_interval: int
    changed_count: Optional[int] = Field(
        default=None, description="换频麦克风数量（status=ok 时有值）"
    )
    frequencies: Optional[List[int]] = Field(
        default=None,
        description="按输入顺序排列的最终频点数组（status=ok 时有值）",
    )
    assignments: Optional[List[Assignment]] = Field(
        default=None, description="逐支麦克风的选频明细（status=ok 时有值）"
    )
    checked_triples: Optional[int] = Field(
        default=None, description="求解过程中校验的有序三元组计数"
    )
    detail: Optional[str] = Field(
        default=None, description="附加说明（status=no_solution 时说明原因）"
    )
