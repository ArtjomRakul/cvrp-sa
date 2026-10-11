"""ALGORITMS: simulētā rūdīšana (SA) un kalnā kāpšana (HC) salīdzinājumam.

Abi ir sliekšņa algoritmi (threshold algorithms) ar vienu un to pašu apkārtni:
  SA: akceptē j, ja  f(j) - f(i) <= 0  vai  rand() < exp(-(f(j)-f(i)) / t_k)
  HC: akceptē j, ja  f(j) - f(i) <= 0                       (t_k = 0)
Temperatūru saraksts ir ģeometrisks: t_k = T0 * alpha^k, katrā līmenī L iterācijas
(kā lekcijā: L[k], t[k]). T0 izvēlas tā, lai vidēji sliktāks gājiens sākumā tiktu
akceptēts ar varbūtību p0; T_beigu = T0 * end_ratio.

Sodu funkcija f = attālums + W * pārkrāvums. W pielāgo katra temperatūras līmeņa beigās
(stratēģiskā oscilācija): ja > 50 % līmeņa iterāciju pavadītas nederīgos risinājumos,
W *= 1,3; ja < 10 %, W *= 0,9 (ne mazāk par W0/4). Tā meklēšana var īslaicīgi šķērsot
nederīgus apgabalus, bet par labāko atzīst tikai derīgu risinājumu.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

from .construction import nearest_neighbour
from .evaluation import route_distance
from .instance import Instance
from .moves import SearchState

DEFAULT_P0 = 0.1          # izvēlēts ar calibrate.py uz instancēm, kas nav testa kopā


@dataclass
class RunResult:
    algorithm: str
    seed: int
    best_cost: float
    best_routes: list[list[int]]
    initial_cost: int
    iterations: int
    time_s: float
    time_to_best_s: float
    history: list[tuple] = field(default_factory=list, repr=False)
    move_counts: list[int] = field(default_factory=list)


def initial_penalty(inst: Instance, routes) -> float:
    """W0: vidēja klienta pārkrāvums maksā ~2 vidējas šķautnes."""
    km = sum(route_distance(inst, r) for r in routes if r)
    avg_edge = km / (inst.n + sum(1 for r in routes if r))
    return 2.0 * avg_edge / (sum(inst.demand) / inst.n)


def solve(inst: Instance, *, algorithm="sa", iterations=1_000_000, seed=0, level_length=None,
          p0=DEFAULT_P0, end_ratio=1e-3, initial_routes=None, record_history=True) -> RunResult:
    rng = random.Random(seed)
    t_start = time.perf_counter()
    init = initial_routes if initial_routes is not None else nearest_neighbour(inst)
    st = SearchState(inst, init)
    initial_cost = st.dist
    W0 = W = initial_penalty(inst, init)
    L = level_length or max(1000, 10 * inst.n)
    levels = max(1, iterations // L)

    if algorithm == "sa":
        worse = []
        for _ in range(2000):
            mv = st.sample(rng)
            if mv is not None:
                df = mv[0] + W * mv[1]
                if df > 0:
                    worse.append(df)
        T0 = (sum(worse) / len(worse)) / math.log(1.0 / p0)
        alpha = end_ratio ** (1.0 / max(1, levels - 1))
    elif algorithm == "hc":
        T0 = alpha = 0.0
    else:
        raise ValueError(algorithm)
    T = T0

    best_cost = st.dist if st.feasible else math.inf
    best_routes = st.snapshot() if st.feasible else []
    t_best = 0.0
    history = []
    exp, rand, sample, apply = math.exp, rng.random, st.sample, st.apply
    it = 0
    for _level in range(levels):
        n_inf = 0
        for _ in range(L):
            mv = sample(rng)
            if mv is not None:
                df = mv[0] + W * mv[1]
                if df <= 0 or (T > 0 and rand() < exp(-df / T)):
                    apply(mv)
                    if st.over_cap == 0 and st.dist < best_cost:
                        best_cost, best_routes = st.dist, st.snapshot()
                        t_best = time.perf_counter() - t_start
            if st.over_cap:
                n_inf += 1
        it += L
        frac = n_inf / L
        if frac > 0.5:
            W *= 1.3
        elif frac < 0.1:
            W = max(W0 / 4, W * 0.9)
        if record_history:
            history.append((it, T, st.dist, st.over_cap, best_cost, W))
        T *= alpha

    return RunResult(algorithm, seed, best_cost, best_routes, initial_cost, it,
                     time.perf_counter() - t_start, t_best, history, list(st.move_counts))
