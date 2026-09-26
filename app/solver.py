"""频点协调求解器。

约束（guard 为保护间隔，单位 kHz）：
1. 任意两支麦克风 i、j：|fi - fj| >= guard
2. 任意三支不同麦克风的有序组合 (i, j, k)：|2*fi - fj - fk| >= guard
   （三阶互调产物 2*fi - fj 不得落在第三支频点的保护间隔内）

优化目标（按优先级）：
1. 最小化"有原频点且被换频"的麦克风数量
2. 在上述前提下，按输入顺序的频点数组取字典序最小

规模上限为 8 支麦克风、每支 6 个候选频点，采用回溯搜索 + 分支限界，
在最坏情况下也能在毫秒级内给出全局最优解。
"""

from typing import List, Optional, Sequence


def solve(
    candidates: Sequence[Sequence[int]],
    originals: Sequence[Optional[int]],
    guard: int,
) -> Optional[List[int]]:
    """求解全局最优频点分配。

    :param candidates: 每支麦克风的候选频点列表（按输入顺序）
    :param originals: 每支麦克风的原频点，无原频点则为 None
    :param guard: 保护间隔（正整数，kHz）
    :return: 最优频点数组（与输入顺序一致）；无解时返回 None
    """
    n = len(candidates)
    # 候选频点去重并升序排列，保证深度优先枚举按"频点字典序"展开
    cands = [sorted(set(c)) for c in candidates]

    assign = [0] * n          # 当前部分分配，仅前 idx 项有效
    best: List[int] = []      # 当前最优完整分配
    best_cost = n + 1         # 当前最优换频数（上界初始化为 n+1）

    def consistent(idx: int, f: int) -> bool:
        """检查第 idx 支麦克风取频点 f 时，与已分配的前 idx 支是否满足全部约束。"""
        # 约束 1：两两频差
        for j in range(idx):
            if abs(f - assign[j]) < guard:
                return False
        # 约束 2：含新麦克风的所有有序三元组。
        # 对无序对 (j, k)，|2*fa - fb - fc| 中"被减/目标"两个角色互换后绝对值相同，
        # 因此每个无序对只需检查三种"谁被加倍"的情形即可覆盖全部有序组合。
        for j in range(idx):
            fj = assign[j]
            for k in range(j + 1, idx):
                fk = assign[k]
                if abs(2 * f - fj - fk) < guard:   # 新频点被加倍
                    return False
                if abs(2 * fj - f - fk) < guard:   # 第 j 支被加倍
                    return False
                if abs(2 * fk - fj - f) < guard:   # 第 k 支被加倍
                    return False
        return True

    def dfs(idx: int, cost: int) -> None:
        nonlocal best, best_cost
        # 分支限界：换频数单调不减，>= 当前最优时不可能更优；
        # 枚举本身按字典序进行，同等换频数下先找到的解字典序更小，无需继续。
        if cost >= best_cost:
            return
        if idx == n:
            best_cost = cost
            best = assign.copy()
            return
        orig = originals[idx]
        for f in cands[idx]:
            if consistent(idx, f):
                assign[idx] = f
                dfs(idx + 1, cost + (0 if orig is not None and f == orig else 1))

    dfs(0, 0)
    return best if best else None
