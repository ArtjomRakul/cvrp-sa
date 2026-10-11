"""Pareizības testi:
  1) katra gājiena paredzētā delta (attālums, pārkrāvums) == faktiskā izmaiņa, un periodiski
     stāvoklis == pilnais pārrēķins (evaluation.evaluate); neviens klients neizkrīt;
  2) publicētie CVRPLIB optimālie maršruti ir derīgi un to attālums sakrīt ar publicēto
     vērtību (pārbauda attālumu noapaļošanas konvenciju un flotes izmēru).
Palaišana:  python -m tests.test_moves
"""
import glob
import random

from cvrp.construction import nearest_neighbour
from cvrp.evaluation import evaluate
from cvrp.instance import read_instance
from cvrp.moves import MOVE_NAMES, SearchState


def check(st, inst):
    s = evaluate(inst, st.routes)
    assert st.dist == s.dist and st.over_cap == s.cap and s.other == 0, (st.dist, s)
    for r, route in enumerate(st.routes):
        for p, c in enumerate(route):
            assert st.rid[c] == r and st.pos[c] == p


def test_deltas(path, steps=20000, seed=1):
    inst = read_instance(path)
    rng = random.Random(seed)
    st = SearchState(inst, nearest_neighbour(inst))
    for k in range(steps):
        mv = st.sample(rng)
        if mv is None:
            continue
        before = (st.dist, st.over_cap)
        st.apply(mv)                       # pielietojam visus (arī sliktos) gājienus
        assert st.dist - before[0] == mv[0], (MOVE_NAMES[mv[2]], mv)
        assert st.over_cap - before[1] == mv[1], (MOVE_NAMES[mv[2]], mv)
        if k % 50 == 0:
            check(st, inst)
    check(st, inst)
    return st.move_counts


if __name__ == "__main__":
    paths = sorted(glob.glob("instances/*.vrp") + glob.glob("instances/calibration/*.vrp"))
    total = 0
    for p in paths:
        mc = test_deltas(p)
        total += sum(mc)
        print(f"OK delta {p}: " + ", ".join(f"{MOVE_NAMES[i]}={mc[i]}" for i in range(4)))
    print(f"Kopā pārbaudīti {total} pielietoti gājieni")
    for p in paths:
        inst = read_instance(p)
        s = evaluate(inst, inst.opt_routes)
        assert s.feasible and s.dist == inst.opt, (inst.name, s, inst.opt)
        print(f"OK {inst.name}: publicētais risinājums derīgs, attālums {s.dist} == {inst.opt:g}")
