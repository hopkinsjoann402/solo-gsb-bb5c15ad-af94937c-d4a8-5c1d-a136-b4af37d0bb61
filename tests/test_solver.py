"""求解器单元测试，含与暴力枚举的随机对拍。"""

import itertools
import random

from app.solver import solve


def brute_force(candidates, originals, guard):
    """暴力枚举全部组合，返回 (最优解 或 None)，用于对拍。"""
    best = None
    best_key = None
    for combo in itertools.product(*[sorted(set(c)) for c in candidates]):
        if not _feasible(combo, guard):
            continue
        cost = sum(
            1 for f, o in zip(combo, originals) if o is not None and f != o
        )
        key = (cost, combo)
        if best_key is None or key < best_key:
            best_key = key
            best = list(combo)
    return best


def _feasible(combo, guard):
    n = len(combo)
    for i in range(n):
        for j in range(n):
            if i != j and abs(combo[i] - combo[j]) < guard:
                return False
    for i, j, k in itertools.permutations(range(n), 3):
        if abs(2 * combo[i] - combo[j] - combo[k]) < guard:
            return False
    return True


def test_pairwise_constraint_infeasible():
    # 两支麦克风候选频点过近，无解
    assert solve([[100], [120]], [None, None], guard=50) is None


def test_third_order_intermod_constraint():
    # 两两频差均 >= 10，但 2*150 = 100 + 200，违反三阶互调约束
    assert solve([[100], [150], [200]], [None, None, None], guard=10) is None
    # 把第三支移开则有解
    assert solve([[100], [150], [210]], [None, None, None], guard=10) == [100, 150, 210]


def test_minimize_changed_count():
    # mic-1 保持原频点 500 时整体可行，不应换频
    result = solve(
        [[500, 900], [700, 1000]],
        [500, None],
        guard=100,
    )
    assert result == [500, 700]


def test_change_only_when_forced():
    # 两支原频点冲突（频差 0 < 100），必须有一支换频；字典序最小方案换第二支
    result = solve(
        [[500, 900], [500, 1000]],
        [500, 500],
        guard=100,
    )
    assert result == [500, 1000]


def test_lexicographic_tie_break():
    # 换频数同为 0 的多个可行解中，取频点数组字典序最小者
    result = solve(
        [[300, 100, 200], [400, 500]],
        [None, None],
        guard=50,
    )
    assert result == [100, 400]


def test_original_not_in_candidates():
    # 原频点不在候选中，必然计一次换频，但仍应给出可行解
    result = solve([[600, 800]], [123], guard=100)
    assert result == [600]


def test_random_against_brute_force():
    rng = random.Random(20260926)
    for _ in range(300):
        n = rng.randint(1, 5)
        candidates = [
            rng.sample(range(400, 460), rng.randint(1, 4)) for _ in range(n)
        ]
        originals = [
            rng.choice(c) if rng.random() < 0.6 else None for c in candidates
        ]
        guard = rng.randint(1, 12)
        assert solve(candidates, originals, guard) == brute_force(
            candidates, originals, guard
        )


def test_max_scale_runs_fast():
    # 上限规模：8 支麦克风、每支 6 个候选，应快速完成
    rng = random.Random(7)
    candidates = [rng.sample(range(470000, 471000), 6) for _ in range(8)]
    originals = [c[0] for c in candidates]
    result = solve(candidates, originals, guard=25)
    assert result is not None
    assert _feasible(result, 25)
