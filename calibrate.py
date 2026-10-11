"""SA sākuma temperatūras kalibrēšana uz instancēm, kas NAV testa kopā (instances/calibration/).

p0 = varbūtība sākumā akceptēt vidēji sliktāku gājienu; salīdzina p0 ∈ {0,5; 0,1; 0,02}
un kalnā kāpšanu (HC), 3 sēklas, budžets 50 000 * n. Izvēlas p0 ar mazāko vidējo novirzi.

  python calibrate.py                  # visas kalibrēšanas instances pēc kārtas (~10 min)
  python calibrate.py X-n110-k13       # tikai viena (var palaist paralēli)
  python calibrate.py --summary        # apkopo results/calibration_*.csv
"""
import csv
import glob
import os
import statistics as stats
import sys

from cvrp.algorithms import solve
from cvrp.construction import nearest_neighbour
from cvrp.evaluation import check_solution
from cvrp.instance import read_instance

INSTANCES = ["X-n110-k13", "X-n153-k22"]
CONFIGS = [("hc", None), ("sa", 0.5), ("sa", 0.1), ("sa", 0.02)]
SEEDS = [1, 2, 3]
OUT = "results"


def label(alg, p0):
    return "HC" if alg == "hc" else f"SA p0={p0}"


def run(name):
    inst = read_instance(os.path.join("instances", "calibration", f"{name}.vrp"))
    init = nearest_neighbour(inst)
    rows = []
    for alg, p0 in CONFIGS:
        for seed in SEEDS:
            kw = {"p0": p0} if p0 is not None else {}
            r = solve(inst, algorithm=alg, iterations=50_000 * inst.n, seed=seed,
                      initial_routes=init, record_history=False, **kw)
            cost = check_solution(inst, r.best_routes).dist
            rows.append(dict(instance=name, config=label(alg, p0), seed=seed, cost=cost,
                             gap_pct=round(100 * (cost - inst.opt) / inst.opt, 3),
                             time_s=round(r.time_s, 1)))
            print(rows[-1], flush=True)
    with open(os.path.join(OUT, f"calibration_{name}.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def summary():
    rows = []
    for p in sorted(glob.glob(os.path.join(OUT, "calibration_*.csv"))):
        with open(p, newline="", encoding="utf-8") as fh:
            rows += list(csv.DictReader(fh))
    with open(os.path.join(OUT, "calibration.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    names = list(dict.fromkeys(r["instance"] for r in rows))
    labels = [label(*c) for c in CONFIGS]

    def mean_gap(name, lab):
        return stats.mean(float(r["gap_pct"]) for r in rows
                          if r["instance"] == name and r["config"] == lab)

    with open(os.path.join(OUT, "calibration.md"), "w", encoding="utf-8") as fh:
        fh.write("Vidējā novirze no optimuma, % (3 sēklas)\n\n| Instance | " + " | ".join(labels)
                 + " |\n|---|" + "---|" * len(labels) + "\n")
        for name in names:
            fh.write(f"| {name} | " + " | ".join(f"{mean_gap(name, l):.2f}" for l in labels) + " |\n")
        overall = {l: stats.mean(mean_gap(nm, l) for nm in names) for l in labels}
        fh.write("| **Vidēji** | " + " | ".join(f"{overall[l]:.2f}" for l in labels) + " |\n")
        best = min((l for l in labels if l != "HC"), key=lambda l: overall[l])
        fh.write(f"\nIzvēlēts: {best}\n")
    print(open(os.path.join(OUT, "calibration.md"), encoding="utf-8").read())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    if args == ["--summary"]:
        summary()
    else:
        for name in args or INSTANCES:
            run(name)
        if not args:
            summary()
