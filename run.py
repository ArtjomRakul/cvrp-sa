"""Vienas instances risināšana.

  python run.py instances/A-n32-k5.vrp
  python run.py instances/X-n101-k25.vrp --alg sa --iters 10000000 --seed 3 --plot marsruti.png
"""
import argparse

from cvrp.algorithms import solve
from cvrp.evaluation import check_solution, route_distance
from cvrp.instance import read_instance, write_sol


def plot_routes(inst, routes, path, title=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xy = inst.coords
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    cmap = plt.get_cmap("tab20")
    for k, r in enumerate(routes):
        pts = [xy[0]] + [xy[c] for c in r] + [xy[0]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", lw=1.1, color=cmap(k % 20))
        ax.scatter([xy[c][0] for c in r], [xy[c][1] for c in r], s=9, color=cmap(k % 20), zorder=3)
    ax.scatter([xy[0][0]], [xy[0][1]], marker="s", s=60, color="black", zorder=4)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--alg", choices=["sa", "hc"], default="sa")
    ap.add_argument("--iters", type=int, default=None, help="noklusēti 50 000 * n")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sol", default=None, help="kur saglabāt risinājumu (.sol)")
    ap.add_argument("--plot", default=None, help="kur saglabāt maršrutu attēlu (.png)")
    a = ap.parse_args()

    inst = read_instance(a.instance)
    res = solve(inst, algorithm=a.alg, iterations=a.iters or 50_000 * inst.n, seed=a.seed)
    s = check_solution(inst, res.best_routes)
    print(f"{inst.name}: n={inst.n}, Q={inst.capacity}, "
          f"K={'neierobežots' if inst.unlimited_fleet else inst.fleet}")
    print(f"sākotnējais (tuvākais kaimiņš): {res.initial_cost}")
    print(f"{a.alg.upper()}: {s.dist} ({len(res.best_routes)} maršruti), laiks {res.time_s:.1f}s, "
          f"iterācijas {res.iterations}")
    if inst.opt:
        print(f"optimums/BKS: {inst.opt:g}, starpība {100 * (s.dist - inst.opt) / inst.opt:.2f}%")
    for k, r in enumerate(res.best_routes, 1):
        load = sum(inst.demand[c] for c in r)
        print(f"  Route #{k} (krava {load}/{inst.capacity}, garums {route_distance(inst, r)}): "
              f"{' '.join(map(str, r))}")
    if a.sol:
        write_sol(a.sol, res.best_routes, s.dist)
    if a.plot:
        plot_routes(inst, res.best_routes, a.plot, f"{inst.name}: {s.dist}")


if __name__ == "__main__":
    main()
