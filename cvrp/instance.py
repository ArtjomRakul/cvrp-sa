"""DOMĒNS: problēmas fakti (problem facts) un CVRPLIB failu nolasīšana.

CVRP (Capacitated Vehicle Routing Problem):
  * depo (mezgls 0), kur visas mašīnas sāk un beidz maršrutu,
  * klienti 1..n ar pieprasījumu q_i (visi JĀAPKALPO, katrs tieši vienu reizi),
  * K vienādas mašīnas ar ietilpību Q,
  * simetriski attālumi; CVRPLIB/TSPLIB konvencija: d_ij = nint(eiklīda attālums),
    tāpēc rezultāti ir tieši salīdzināmi ar publicētajiem optimumiem.
Flote: klasiskajām kopām (A, B, E, F, M, P) K = k no nosaukuma (-kK); X kopai flote nav
ierobežota (literatūras konvencija) - tad K = n (vairāk maršrutu nekā klientu nevar būt).
Maršruta beigas modelē ar virtuālu mezglu E = n+1: D[c][E] = d(c, 0), D[0][E] = 0
(tukšs maršruts neko nemaksā). Optimālā / labākā zināmā vērtība no .sol faila ("Cost").
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field


@dataclass
class Instance:
    name: str
    n: int                          # klientu skaits (bez depo)
    fleet: int                      # K (X kopai = n, t.i., neierobežota)
    capacity: int                   # Q
    demand: list[int]               # q_i, q_0 = 0
    coords: list[tuple[float, float]]
    dist: list[list[int]]           # (n+2) x (n+2), ieskaitot E = n+1
    unlimited_fleet: bool = False
    opt: float | None = None        # publicētā optimālā / labākā zināmā vērtība
    opt_routes: list[list[int]] | None = field(default=None, repr=False)

    @property
    def E(self) -> int:
        return self.n + 1


def read_instance(path: str) -> Instance:
    with open(path, encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh.read().replace("\r", "").split("\n")]
    header: dict[str, str] = {}
    sec: dict[str, list[str]] = {}
    cur = None
    for ln in lines:
        if not ln or ln == "EOF" or ln.startswith("#"):
            continue
        if ln.endswith("_SECTION"):
            cur = ln
            sec[cur] = []
        elif re.match(r"^[A-Z_]+\s*:", ln):
            k, v = ln.split(":", 1)
            header[k.strip()] = v.strip()
            cur = None
        elif cur is not None:
            sec[cur].append(ln)

    assert header.get("EDGE_WEIGHT_TYPE", "EUC_2D") == "EUC_2D", "atbalstīts tikai EUC_2D"
    name = header.get("NAME", os.path.splitext(os.path.basename(path))[0])
    dim = int(header["DIMENSION"])
    n = dim - 1
    if "DEPOT_SECTION" in sec:
        assert int(sec["DEPOT_SECTION"][0].split()[0]) == 1, "sagaidām depo kā 1. mezglu"

    coords = [(0.0, 0.0)] * dim
    for ln in sec["NODE_COORD_SECTION"]:
        idx, x, y = ln.split()[:3]
        coords[int(idx) - 1] = (float(x), float(y))
    demand = [0] * dim
    for ln in sec["DEMAND_SECTION"]:
        idx, q = ln.split()[:2]
        demand[int(idx) - 1] = int(q)
    demand[0] = 0

    base = [[int(math.hypot(a[0] - b[0], a[1] - b[1]) + 0.5) for b in coords] for a in coords]
    dist = [row + [row[0] if i else 0] for i, row in enumerate(base)]       # D[c][E] = d(c, 0)
    dist.append([base[c][0] if c else 0 for c in range(dim)] + [0])         # D[0][E] = 0

    m = re.search(r"-k(\d+)", name)
    unlimited = name.startswith("X-") or m is None
    inst = Instance(name=name, n=n, fleet=n if unlimited else int(m.group(1)),
                    capacity=int(header["CAPACITY"]), demand=demand, coords=coords, dist=dist,
                    unlimited_fleet=unlimited)
    sol = os.path.splitext(path)[0] + ".sol"
    if os.path.exists(sol):
        inst.opt, inst.opt_routes = read_sol(sol)
    return inst


def read_sol(path: str):
    routes, cost = [], None
    with open(path, encoding="utf-8") as fh:
        for ln in fh.read().replace("\r", "").split("\n"):
            if ln.lower().startswith("route"):
                routes.append([int(t) for t in ln.split(":", 1)[1].split()])
            elif ln.lower().startswith("cost"):
                cost = float(ln.split()[1])
    return cost, routes


def write_sol(path: str, routes: list[list[int]], cost: float) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for k, r in enumerate(routes, 1):
            fh.write(f"Route #{k}: {' '.join(map(str, r))}\n")
        fh.write(f"Cost {cost:g}\n")
