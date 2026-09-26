"""求解器单元测试。"""
import pytest

from app.solver import solve


def check_constraints(freqs, guard):
    """暴力校验一组频点是否满足全部约束（用于测试交叉验证）。"""
    n = len(freqs)
    for i in range(n):
        for j in range(n):
            if i != j:
                assert abs(freqs[i] - freqs[j]) >= guard
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if len({i, j, k}) == 3:
                    assert abs(2 * freqs[i] - freqs[j] - freqs[k]) >= guard


def brute_force_best(candidates, originals, guard):
    """全枚举求最优解，作为求解器的对照实现。"""
    import itertools

    best = None
    for combo in itertools.product(*[sorted(set(c)) for c in candidates]):
        n = len(combo)
        ok = True
        for i in range(n):
            for j in range(n):
                if i != j and abs(combo[i] - combo[j]) < guard:
                    ok = False
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    if len({i, j, k}) == 3 and abs(2 * combo[i] - combo[j] - combo[k]) < guard:
                        ok = False
        if not ok:
            continue
        changes = sum(
            1 for f, o in zip(combo, originals) if o is not None and f != o
        )
        key = (changes, combo)
        if best is None or key < best:
            best = key
    return best


class TestConstraints:
    def test_pairwise_spacing(self):
        # 两支麦克风，保护间隔 100：只有 (100, 250) 可行
        r = solve([[100], [150, 250]], [None, None], 100)
        assert r.feasible
        assert r.frequencies == [100, 250]
        check_constraints(r.frequencies, 100)

    def test_intermod_triple_constraint(self):
        # 500/600/750 两两频差均 >= 100，但 |2*600-500-750| = 50 < 100 → 无解
        r = solve([[500], [600], [750]], [None, None, None], 100)
        assert not r.feasible

    def test_intermod_ordered_all_positions(self):
        # 有序遍历：被加倍的可以是任意一支
        # 500/700/950：|2*500-700-950|=650, |2*700-500-950|=50, |2*950-500-700|=700
        # guard=51 时中间支被加倍的情形 50 < 51 → 无解
        r = solve([[500], [700], [950]], [None, None, None], 51)
        assert not r.feasible
        # guard=50 时全部满足 → 有解
        r = solve([[500], [700], [950]], [None, None, None], 50)
        assert r.feasible
        check_constraints(r.frequencies, 50)

    def test_no_solution_pairwise(self):
        r = solve([[100], [200]], [None, None], 1000)
        assert not r.feasible
        assert r.frequencies is None
        assert r.changed_count is None


class TestObjective:
    def test_minimize_changes_first(self):
        # (100,300) 换频 0 次，优于 (100,150) 换频 1 次
        r = solve(
            [[100, 200], [150, 300]],
            [100, 300],
            guard=10,
        )
        assert r.frequencies == [100, 300]
        assert r.changed_count == 0

    def test_lexicographic_tiebreak(self):
        # 原频点不在候选中 → 必然换频 1 次；两个方案换频数相同，取字典序最小
        r = solve(
            [[100, 200], [150, 250]],
            [300, None],
            guard=10,
        )
        assert r.frequencies == [100, 150]
        assert r.changed_count == 1

    def test_original_not_in_candidates_counts_as_changed(self):
        r = solve([[500]], [999], guard=10)
        assert r.feasible
        assert r.changed_count == 1

    def test_no_originals_lexicographic_min(self):
        r = solve(
            [[200, 100], [250, 150]],  # 未排序输入也应得到升序字典序最小
            [None, None],
            guard=10,
        )
        assert r.frequencies == [100, 150]
        assert r.changed_count == 0


class TestAgainstBruteForce:
    """随机用例与全枚举对照，验证全局最优性。"""

    @pytest.mark.parametrize("seed", range(30))
    def test_random_matches_brute_force(self, seed):
        import random

        rng = random.Random(seed)
        n = rng.randint(1, 5)
        candidates = [
            sorted(rng.sample(range(100, 1000, 25), rng.randint(1, 6)))
            for _ in range(n)
        ]
        originals = [
            rng.choice([None, rng.randint(100, 975)]) for _ in range(n)
        ]
        guard = rng.choice([10, 25, 50, 75, 100])

        r = solve(candidates, originals, guard)
        best = brute_force_best(candidates, originals, guard)

        if best is None:
            assert not r.feasible
        else:
            assert r.feasible
            assert r.changed_count == best[0]
            assert tuple(r.frequencies) == best[1]
            check_constraints(r.frequencies, guard)


class TestInputValidation:
    def test_invalid_guard(self):
        with pytest.raises(ValueError):
            solve([[100]], [None], 0)

    def test_too_many_mics(self):
        with pytest.raises(ValueError):
            solve([[100]] * 9, [None] * 9, 10)

    def test_too_many_candidates(self):
        with pytest.raises(ValueError):
            solve([[1, 2, 3, 4, 5, 6, 7]], [None], 10)

    def test_empty_candidates(self):
        with pytest.raises(ValueError):
            solve([[]], [None], 10)


class TestScale:
    def test_eight_mics_six_candidates(self):
        # 上界规模：8 支 x 6 候选，应快速求解
        # 原频点按 2 的幂间隔排布，其自身即满足全部约束（含三频互调），
        # 因此最优解必然是 0 支换频、全部保留原频点
        originals = [1000 * (2 ** i) for i in range(8)]
        candidates = [[f + k * 100 for k in range(6)] for f in originals]
        r = solve(candidates, originals, guard=300)
        assert r.feasible
        assert r.changed_count == 0
        assert r.frequencies == originals
        check_constraints(r.frequencies, 300)
