"""NOVĒRTĒŠANA: pilna (ne-inkrementāla) izmaksu funkcija un neatkarīgs pārbaudītājs.

Divlīmeņu novērtējums (kā Timefold HardSoftScore):
  hard (pārkāpumu APMĒRS):
     cap   = sum_r max(0, load(r) - Q)            ietilpības pārsniegums
     other = neapkalpoti / dublēti klienti + maršruti virs K (iebūvēti ierobežojumi -
             meklēšanā tie nekad nerodas, bet pārbaudītājs tos pārbauda neatkarīgi)
  soft = kopējais nobrauktais attālums sum_r d(r)
Risinājums ir derīgs (feasible), ja hard = 0. Meklēšanā lieto skalāru sodu funkciju
f = soft + W * cap (sk. algorithms.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from .instance import Instance


@dataclass
class Score:
    cap: int
    other: int
    dist: int

    @property
    def feasible(self) -> bool:
        return self.cap == 0 and self.other == 0


def route_distance(inst: Instance, r: list[int]) -> int:
    if not r:
        return 0
    D = inst.dist
    return D[0][r[0]] + sum(D[a][b] for a, b in zip(r, r[1:])) + D[r[-1]][inst.E]


def evaluate(inst: Instance, routes: list[list[int]]) -> Score:
    cap = dist = 0
    seen = [0] * (inst.n + 1)
    non_empty = [r for r in routes if r]
    for r in non_empty:
        cap += max(0, sum(inst.demand[c] for c in r) - inst.capacity)
        dist += route_distance(inst, r)
        for c in r:
            seen[c] += 1
    other = sum(abs(s - 1) for s in seen[1:]) + max(0, len(non_empty) - inst.fleet)
    return Score(cap, other, dist)


def check_solution(inst: Instance, routes: list[list[int]]) -> Score:
    """Neatkarīga pārbaude - izmet kļūdu, ja risinājums nav derīgs."""
    s = evaluate(inst, routes)
    if not s.feasible:
        raise AssertionError(f"{inst.name}: risinājums nav derīgs ({s})")
    return s
