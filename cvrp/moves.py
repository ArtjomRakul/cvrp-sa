"""GĀJIENS: apkārtnes funkcija un inkrementāla (delta) novērtēšana.

Stāvoklis (planning solution):
  routes[r]   - r-tās mašīnas klientu secība (plānošanas mainīgais: saraksts)
Izrēķināmās īpašības (shadow), pārrēķina tikai gājienā iesaistītajam(-iem) maršrutam(-iem):
  rid[c], pos[c], cum[c] - klienta maršruts, pozīcija, kumulatīvā krava līdz c ieskaitot
  load[r], rdist[r]      - maršruta krava un garums

Gājieni (visi novērtējami O(1), mainot tikai 2-4 šķautnes un 1-2 kravas):
  RELOCATE - pārvieto 1..3 pēc kārtas esošu klientu segmentu (iespējams apgrieztu) uz citu
             vietu tajā pašā vai citā maršrutā (ChangeMove / Or-opt); 3 % - uz tukšu mašīnu
  SWAP     - samaina vietām divus klientus (SwapMove)
  2-OPT    - apgriež segmentu viena maršruta ietvaros
  2-OPT*   - samaina divu maršrutu "astes"
Granulārā apkārtne: partneri v klientam c ar varbūtību 0,9 ņem no c tuvāko kaimiņu
saraksta, un gājienu konstruē tā, lai c un v kļūtu blakus (jauna šķautne (c, v)).
Gājiens = (d_attālums, d_pārkrāvums, tips, argumenti).
"""
from __future__ import annotations

from .instance import Instance

RELOCATE, SWAP, TWO_OPT, TWO_OPT_STAR = range(4)
MOVE_NAMES = ["relocate", "swap", "2-opt", "2-opt*"]


class SearchState:
    def __init__(self, inst: Instance, routes, *, n_neighbours=15, p_neighbour=0.9,
                 probs=(0.40, 0.25)):
        self.inst = inst
        self.D, self.dem, self.Q, self.n, self.E = inst.dist, inst.demand, inst.capacity, inst.n, inst.E
        self.p_neighbour = p_neighbour
        self.p_rel = probs[0]                     # relocate | swap | 2-opt / 2-opt*
        self.p_swap = probs[0] + probs[1]
        D = self.D
        k = min(n_neighbours, self.n - 1)
        self.neigh = [[]] + [sorted((v for v in range(1, self.n + 1) if v != c),
                                    key=lambda v: (D[c][v], v))[:k] for c in range(1, self.n + 1)]
        self.routes = [list(r) for r in routes if r]
        assert len(self.routes) <= inst.fleet
        self.routes += [[] for _ in range(inst.fleet - len(self.routes))]
        size = self.n + 1
        self.rid, self.pos, self.cum = [-1] * size, [-1] * size, [0] * size
        m = inst.fleet
        self.load, self.rdist = [0] * m, [0] * m
        self.dist = self.over_cap = 0
        for r in range(m):
            self._reindex(r)
            self._account(r)
        assert all(self.rid[c] >= 0 for c in range(1, size)), "visi klienti jāapkalpo"
        self.n_empty = sum(1 for r in self.routes if not r)
        self.move_counts = [0] * 4

    # ------------------------------------------------------------------ utils
    def _ov(self, l):
        return l - self.Q if l > self.Q else 0

    def _reindex(self, r):
        rid, pos, cum, D = self.rid, self.pos, self.cum, self.D
        acc, dacc, prev = 0, 0, 0
        for i, c in enumerate(self.routes[r]):
            rid[c], pos[c] = r, i
            acc += self.dem[c]
            cum[c] = acc
            dacc += D[prev][c]
            prev = c
        self.load[r] = acc
        self.rdist[r] = dacc + D[prev][self.E]

    def _account(self, r, sign=1):
        self.dist += sign * self.rdist[r]
        self.over_cap += sign * self._ov(self.load[r])

    @property
    def feasible(self):
        return self.over_cap == 0

    def snapshot(self):
        return [list(r) for r in self.routes if r]

    def _partner(self, c, rng):
        if rng.random() < self.p_neighbour:
            nb = self.neigh[c]
            return nb[int(rng.random() * len(nb))]
        v = 1 + int(rng.random() * self.n)
        return v if v != c else None

    def _nb(self, r, i):
        """(iepriekšējais, nākamais) mezgls ap pozīciju i maršrutā r."""
        R = self.routes[r]
        return (R[i - 1] if i > 0 else 0), (R[i + 1] if i + 1 < len(R) else self.E)

    # ---------------------------------------------------------- ģenerēšana
    def sample(self, rng):
        c = 1 + int(rng.random() * self.n)
        u = rng.random()
        if u < self.p_rel:
            return self._relocate(c, rng)
        if u < self.p_swap:
            return self._swap(c, rng)
        return self._two_opt(c, rng)

    def _relocate(self, c, rng):
        D, routes, rid, pos, E = self.D, self.routes, self.rid, self.pos, self.E
        r1, i = rid[c], pos[c]
        R1 = routes[r1]
        m1 = len(R1)
        x = rng.random()
        L = 1 if x < 0.6 else (2 if x < 0.85 else 3)
        L = min(L, m1 - i)
        s0, sl = c, R1[i + L - 1]
        a = R1[i - 1] if i > 0 else 0
        b = R1[i + L] if i + L < m1 else E
        rev = L > 1 and rng.random() < 0.5
        if self.n_empty and rng.random() < 0.03:          # "atver" jaunu mašīnu
            r2 = next(r for r, R in enumerate(routes) if not R)
            p, q = 0, E
        else:
            v = self._partner(c, rng)
            if v is None:
                return None
            r2, j = rid[v], pos[v]
            if r2 == r1 and i <= j < i + L:
                return None
            pv, nv = self._nb(r2, j)
            p, q = (v, nv) if rng.random() < 0.5 else (pv, v)
            if r2 == r1 and (q == s0 or p == sl):
                return None                               # tā pati vieta
        x0, y0 = (sl, s0) if rev else (s0, sl)
        dd = (D[a][b] - D[a][s0] - D[sl][b]) + (D[p][x0] + D[y0][q] - D[p][q])
        if r1 == r2:
            return dd, 0, RELOCATE, (r1, i, L, r2, p, rev)
        seg = self.cum[sl] - (self.cum[a] if i > 0 else 0)
        l1, l2, ov = self.load[r1], self.load[r2], self._ov
        return dd, ov(l1 - seg) - ov(l1) + ov(l2 + seg) - ov(l2), RELOCATE, (r1, i, L, r2, p, rev)

    def _swap(self, c, rng):
        D, rid, pos = self.D, self.rid, self.pos
        v = self._partner(c, rng)
        if v is None:
            return None
        pv, nv = self._nb(rid[v], pos[v])
        t = rng.random()                                  # c <-> v vai c <-> v kaimiņš
        w = v if t < 0.34 else (pv if t < 0.67 else nv)
        if w == 0 or w == self.E:
            w = v
        if w == c:
            return None
        u = c
        r1, i, r2, j = rid[u], pos[u], rid[w], pos[w]
        if r1 == r2 and j < i:
            u, w, i, j = w, u, j, i
        pu, nu = self._nb(r1, i)
        pw, nw = self._nb(r2, j)
        if r1 == r2:
            if j == i + 1:
                dd = D[pu][w] + D[u][nw] - D[pu][u] - D[w][nw]
            else:
                dd = (D[pu][w] + D[w][nu] - D[pu][u] - D[u][nu]
                      + D[pw][u] + D[u][nw] - D[pw][w] - D[w][nw])
            return dd, 0, SWAP, (u, w)
        dd = (D[pu][w] + D[w][nu] - D[pu][u] - D[u][nu]
              + D[pw][u] + D[u][nw] - D[pw][w] - D[w][nw])
        diff = self.dem[w] - self.dem[u]
        l1, l2, ov = self.load[r1], self.load[r2], self._ov
        return dd, ov(l1 + diff) - ov(l1) + ov(l2 - diff) - ov(l2), SWAP, (u, w)

    def _two_opt(self, c, rng):
        D, routes, rid, pos, E = self.D, self.routes, self.rid, self.pos, self.E
        v = self._partner(c, rng)
        if v is None:
            return None
        r1, r2, i, j = rid[c], rid[v], pos[c], pos[v]
        if r1 == r2:                                      # 2-opt: jauna šķautne (c, v)
            R = routes[r1]
            if abs(i - j) == 1:
                return None
            if i < j:
                a, b, e, f, s, t = c, R[i + 1], v, (R[j + 1] if j + 1 < len(R) else E), i + 1, j
            else:
                a, b, e, f, s, t = (R[j - 1] if j > 0 else 0), v, R[i - 1], c, j, i - 1
            return D[a][e] + D[b][f] - D[a][b] - D[e][f], 0, TWO_OPT, (r1, s, t)
        R1, R2 = routes[r1], routes[r2]                  # 2-opt*: R1[:i+1]+R2[j:], R2[:j]+R1[i+1:]
        n1 = R1[i + 1] if i + 1 < len(R1) else E
        p2 = R2[j - 1] if j > 0 else 0
        dd = D[c][v] + D[p2][n1] - D[c][n1] - D[p2][v]
        l1, l2, ov = self.load[r1], self.load[r2], self._ov
        h1, h2 = self.cum[c], (self.cum[p2] if j > 0 else 0)
        dcap = ov(h1 + l2 - h2) + ov(h2 + l1 - h1) - ov(l1) - ov(l2)
        return dd, dcap, TWO_OPT_STAR, (r1, i, r2, j)

    # ------------------------------------------------------------ pielietošana
    def apply(self, mv):
        kind, args = mv[2], mv[3]
        routes, rid, pos = self.routes, self.rid, self.pos
        if kind == RELOCATE:
            touched = (args[0],) if args[0] == args[3] else (args[0], args[3])
        elif kind == SWAP:
            r1, r2 = rid[args[0]], rid[args[1]]
            touched = (r1,) if r1 == r2 else (r1, r2)
        elif kind == TWO_OPT:
            touched = (args[0],)
        else:
            touched = (args[0], args[2])
        empty_before = sum(1 for r in touched if not routes[r])
        for r in touched:
            self._account(r, -1)

        if kind == RELOCATE:
            r1, i, L, r2, p, rev = args
            seg = routes[r1][i:i + L]
            del routes[r1][i:i + L]
            if rev:
                seg.reverse()
            R2 = routes[r2]
            k = 0 if p == 0 else R2.index(p) + 1
            R2[k:k] = seg
        elif kind == SWAP:
            u, w = args
            i, j = pos[u], pos[w]
            routes[rid[u]][i], routes[rid[w]][j] = w, u
        elif kind == TWO_OPT:
            r, s, t = args
            routes[r][s:t + 1] = routes[r][s:t + 1][::-1]
        else:
            r1, i, r2, j = args
            R1, R2 = routes[r1], routes[r2]
            routes[r1], routes[r2] = R1[:i + 1] + R2[j:], R2[:j] + R1[i + 1:]

        for r in touched:
            self._reindex(r)
            self._account(r, +1)
        self.n_empty += sum(1 for r in touched if not routes[r]) - empty_before
        self.move_counts[kind] += 1
