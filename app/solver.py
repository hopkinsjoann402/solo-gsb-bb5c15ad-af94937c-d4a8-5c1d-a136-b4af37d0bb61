"""频点协调求解器。

约束（g = 保护间隔，单位 kHz）：
1. 任意两支麦克风 i、j：|fi - fj| >= g
2. 任意三支不同麦克风，遍历全部有序三元组 (i, j, k)：|2fi - fj - fk| >= g

目标（全局最优，按优先级）：
1. 最小化换频数量（提供了原频点且最终频点 != 原频点的麦克风数）
2. 在上述前提下，按输入顺序的频点数组取字典序最小

规模上限 8 支麦克风 x 6 个候选频点，采用按输入顺序的回溯搜索 +
分支定界剪枝，可在毫秒内求得全局最优解。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


@dataclass
class SolveResult:
    """求解结果。solutions 为 None 表示无解。"""

    frequencies: Optional[List[int]]
    changed_count: Optional[int]
    checked_triples: int = 0

    @property
    def feasible(self) -> bool:
        return self.frequencies is not None


@dataclass
class _State:
    """回溯搜索的共享状态。"""

    n: int
    guard: int
    candidates: List[List[int]]  # 每支麦克风去重升序后的候选频点
    originals: List[Optional[int]]
    assignment: List[int] = field(default_factory=list)
    best_key: Optional[Tuple[int, Tuple[int, ...]]] = None
    checked_triples: int = 0


def _consistent(state: _State, idx: int) -> bool:
    """检查第 idx 支麦克风的当前赋值是否与 0..idx-1 的赋值满足全部约束。

    覆盖所有包含 idx 的约束；不含 idx 的约束在之前的递归层已验证。
    """
    g = state.guard
    a = state.assignment
    fi = a[idx]

    # 约束 1：两两频差
    for j in range(idx):
        if abs(fi - a[j]) < g:
            return False

    # 约束 2：包含 idx 的全部有序三元组
    for x in range(idx):
        for y in range(idx):
            if x == y:
                continue
            fx, fy = a[x], a[y]
            state.checked_triples += 2
            # idx 为被加倍的麦克风：|2fi - fx - fy| >= g
            if abs(2 * fi - fx - fy) < g:
                return False
            # x 为被加倍的麦克风：|2fx - fy - fi| >= g
            # （y 被加倍的情形在交换 x、y 的迭代中覆盖）
            if abs(2 * fx - fy - fi) < g:
                return False
    return True


def _dfs(state: _State, idx: int, changes: int) -> None:
    best = state.best_key
    if best is not None and changes > best[0]:
        return  # 换频数已超当前最优，剪枝

    if idx == state.n:
        key = (changes, tuple(state.assignment))
        if best is None or key < best:
            state.best_key = key
        return

    if best is not None and changes == best[0]:
        # 换频数持平最优时，若当前前缀字典序已大于最优前缀，剪枝
        if tuple(state.assignment[:idx]) > best[1][:idx]:
            return

    original = state.originals[idx]
    for f in state.candidates[idx]:
        state.assignment.append(f)
        new_changes = changes
        if original is not None and f != original:
            new_changes += 1
        if state.best_key is None or new_changes <= state.best_key[0]:
            if _consistent(state, idx):
                _dfs(state, idx + 1, new_changes)
        state.assignment.pop()


def solve(
    candidates: Sequence[Sequence[int]],
    originals: Sequence[Optional[int]],
    guard: int,
) -> SolveResult:
    """求解频点协调问题。

    参数：
        candidates: 每支麦克风的候选频点列表（kHz 整数）
        originals:  每支麦克风的原频点，未提供则为 None
        guard:      保护间隔（kHz 正整数）

    返回：
        SolveResult；feasible 为 False 时 frequencies/changed_count 为 None
    """
    if guard <= 0:
        raise ValueError("guard 必须为正整数")
    n = len(candidates)
    if not 1 <= n <= 8:
        raise ValueError("麦克风数量须在 1~8 之间")
    if len(originals) != n:
        raise ValueError("originals 长度必须与 candidates 一致")

    state = _State(
        n=n,
        guard=guard,
        candidates=[sorted(set(c)) for c in candidates],
        originals=list(originals),
    )
    for c in state.candidates:
        if not 1 <= len(c) <= 6:
            raise ValueError("每支麦克风的候选频点须在 1~6 个之间")

    _dfs(state, 0, 0)

    if state.best_key is None:
        return SolveResult(
            frequencies=None,
            changed_count=None,
            checked_triples=state.checked_triples,
        )
    changes, freqs = state.best_key
    return SolveResult(
        frequencies=list(freqs),
        changed_count=changes,
        checked_triples=state.checked_triples,
    )
