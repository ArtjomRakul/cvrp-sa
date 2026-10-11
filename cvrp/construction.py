"""Sākotnējā risinājuma konstruēšana - tuvākā kaimiņa heiristika.

Mašīna no depo dodas uz tuvāko vēl neapkalpoto klientu, kura pieprasījums vēl ietilpst;
ja tāda nav, atgriežas depo un sāk nākamā mašīna. Ja flote ir fiksēta (K) un mašīnas
beidzas, atlikušos klientus pievieno vismazāk noslogotajam maršrutam - sākums var būt
nederīgs, to salabo meklēšana, jo pārkrāvums ir sodīts izmaksu funkcijā.
"""
from __future__ import annotations

from .instance import Instance


def nearest_neighbour(inst: Instance) -> list[list[int]]:
    D, dem, Q = inst.dist, inst.demand, inst.capacity
    unvisited = set(range(1, inst.n + 1))
    routes: list[list[int]] = []
    while unvisited:
        if len(routes) == inst.fleet:
            for c in sorted(unvisited, key=lambda c: (-dem[c], c)):
                min(routes, key=lambda r: sum(dem[x] for x in r)).append(c)
            break
        route, load, cur = [], 0, 0
        while True:
            cands = [c for c in unvisited if load + dem[c] <= Q]
            if not cands:
                break
            nxt = min(cands, key=lambda c: (D[cur][c], c))
            route.append(nxt)
            load += dem[nxt]
            unvisited.remove(nxt)
            cur = nxt
        if not route:                     # klients vienatnē neietilpst (CVRPLIB tā nav)
            route = [min(unvisited)]
            unvisited.remove(route[0])
        routes.append(route)
    return routes
