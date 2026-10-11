"""Testēšana: 8 CVRPLIB instances x abi algoritmi (SA, HC) x 5 sēklas.

  python experiments.py               # pilnā testēšana (~15-30 min vienā CPU kodolā)
  python experiments.py --quick       # ātrā pārbaude (10x mazāk iterāciju, 2 sēklas)
  python experiments.py --only X-n200-k36 X-n157-k13    # tikai dažas (var palaist paralēli)

Atskaites vērtība f* katrai instancei ir publicētā optimālā / labākā zināmā vērtība no
CVRPLIB (.sol fails); pirms testēšanas pārbauda, ka publicētais risinājums ir derīgs un tā
attālums mūsu modelī sakrīt ar f*.
Rezultāti: results/runs.csv, summary.csv, summary.md, environment.json, solutions/*.sol,
history_*.csv. Pārtraukta palaišana turpina no results/parts/ (dzēsiet to, lai rēķinātu no jauna).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import statistics as stats
import subprocess
import time

from cvrp.algorithms import DEFAULT_P0, solve
from cvrp.construction import nearest_neighbour
from cvrp.evaluation import check_solution, evaluate
from cvrp.instance import read_instance, write_sol

INSTANCES = ["P-n16-k8", "A-n32-k5", "F-n72-k4", "M-n101-k10",
             "X-n101-k25", "X-n120-k6", "X-n157-k13", "X-n200-k36"]
ALGORITHMS = ["sa", "hc"]
ITERS_PER_CUSTOMER = 50_000
HISTORY_INSTANCE = "X-n200-k36"


def cpu_name() -> str:
    """Procesora nosaukums (Windows / Linux / macOS) - lai zinātu, kur mērīti izpildes laiki."""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
        elif platform.system() == "Darwin":
            name = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
        else:
            with open("/proc/cpuinfo", encoding="utf-8") as fh:
                name = next(ln.split(":", 1)[1] for ln in fh if ln.startswith("model name"))
    except Exception:  # noqa: BLE001 - informatīvi, nekritiski
        name = platform.processor() or "nezināms procesors"
    return re.sub(r"\s+", " ", re.sub(r"\((R|TM|tm|r)\)|CPU", "", name)).strip()


def gap(cost, opt):
    return round(100.0 * (cost - opt) / opt, 3)


def run_instance(name, per, seeds, out, log):
    inst = read_instance(os.path.join("instances", f"{name}.vrp"))
    ref = check_solution(inst, inst.opt_routes)          # publicētais risinājums ir derīgs
    assert ref.dist == inst.opt, "attālumu konvencija nesakrīt ar CVRPLIB"
    iters = per * inst.n
    init = nearest_neighbour(inst)
    s0 = evaluate(inst, init)
    rows = [dict(instance=name, n=inst.n, algorithm="nn", seed=0, iterations=0, time_s=0,
                 time_to_best_s=0, cost=s0.dist if s0.feasible else "", routes=len(init),
                 opt=inst.opt, gap_pct=gap(s0.dist, inst.opt) if s0.feasible else "")]
    best = None
    for alg in ALGORITHMS:
        for seed in seeds:
            r = solve(inst, algorithm=alg, iterations=iters, seed=seed, initial_routes=init,
                      record_history=(name == HISTORY_INSTANCE and seed == 1))
            s = check_solution(inst, r.best_routes)       # neatkarīga pārbaude
            assert s.dist == r.best_cost and s.dist >= inst.opt
            rows.append(dict(instance=name, n=inst.n, algorithm=alg, seed=seed,
                             iterations=r.iterations, time_s=round(r.time_s, 2),
                             time_to_best_s=round(r.time_to_best_s, 2), cost=s.dist,
                             routes=len(r.best_routes), opt=inst.opt, gap_pct=gap(s.dist, inst.opt)))
            log(f"{name} {alg} seed={seed} -> {s.dist} ({gap(s.dist, inst.opt):.2f}%) t={r.time_s:.1f}s")
            if alg == "sa" and (best is None or s.dist < best[0]):
                best = (s.dist, r.best_routes)
            if r.history:
                with open(os.path.join(out, f"history_{name}_{alg}.csv"), "w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["iteration", "temperature", "current_dist", "over_cap",
                                "best_dist", "penalty_W"])
                    w.writerows(r.history)
    write_sol(os.path.join(out, "solutions", f"{name}.sol"), best[1], best[0])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    per = ITERS_PER_CUSTOMER // (10 if a.quick else 1)
    seeds = list(range(1, (2 if a.quick else a.seeds) + 1))
    parts = os.path.join(a.out, "parts")
    os.makedirs(os.path.join(a.out, "solutions"), exist_ok=True)
    os.makedirs(parts, exist_ok=True)
    env = dict(cpu=cpu_name(), python=platform.python_version(),
               os=f"{platform.system()} {platform.release()}", date=time.strftime("%Y-%m-%d"),
               iters_per_customer=per, seeds=len(seeds), p0=DEFAULT_P0)
    with open(os.path.join(a.out, "environment.json"), "w", encoding="utf-8") as fh:
        json.dump(env, fh, ensure_ascii=False, indent=1)
    t0 = time.time()

    def log(msg):
        print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)

    log(f"{env['cpu']}, Python {env['python']}, {env['os']}")
    rows = []
    for name in INSTANCES:
        part = os.path.join(parts, f"{name}.json")
        if os.path.exists(part):
            with open(part, encoding="utf-8") as fh:
                rows += json.load(fh)
            continue
        if a.only is not None and name not in a.only:
            continue
        group = run_instance(name, per, seeds, a.out, log)
        with open(part, "w", encoding="utf-8") as fh:
            json.dump(group, fh)
        rows += group
    if a.only is not None and {r["instance"] for r in rows} != set(INSTANCES):
        log("daļēja palaišana pabeigta; kopsavilkumu veido pēc visām instancēm")
        return
    with open(os.path.join(a.out, "runs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summarize(rows, a.out)


def summarize(rows, out):
    summ = []
    for name in INSTANCES:
        rs = [r for r in rows if r["instance"] == name]
        nn = rs[0]
        inst = read_instance(os.path.join("instances", f"{name}.vrp"))
        e = dict(instance=name, n=inst.n, K="-" if inst.unlimited_fleet else inst.fleet,
                 Q=inst.capacity, opt=inst.opt, nn_cost=nn["cost"], nn_gap=nn["gap_pct"])
        for alg in ALGORITHMS:
            sub = [r for r in rs if r["algorithm"] == alg]
            costs = [r["cost"] for r in sub]
            gaps = [r["gap_pct"] for r in sub]
            e.update({f"{alg}_best": min(costs), f"{alg}_avg": round(stats.mean(costs), 1),
                      f"{alg}_spread": max(costs) - min(costs),
                      f"{alg}_best_gap": round(min(gaps), 2), f"{alg}_avg_gap": round(stats.mean(gaps), 2),
                      f"{alg}_hits": sum(1 for x in gaps if x <= 1e-9), f"{alg}_runs": len(sub),
                      f"{alg}_time": round(stats.mean(r["time_s"] for r in sub), 1),
                      f"{alg}_ttb": round(stats.mean(r["time_to_best_s"] for r in sub), 1)})
        summ.append(e)
    with open(os.path.join(out, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summ[0].keys()))
        w.writeheader()
        w.writerows(summ)
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("| Instance | n | K | f* | NN gap % | HC vid. gap % | SA labākais (gap %) | "
                 "SA vid. gap % | SA trāpa f* | SA laiks s |\n|" + "---|" * 10 + "\n")
        for e in summ:
            fh.write(f"| {e['instance']} | {e['n']} | {e['K']} | {e['opt']:g} | {e['nn_gap']} | "
                     f"{e['hc_avg_gap']} | {e['sa_best']} ({e['sa_best_gap']}) | {e['sa_avg_gap']} | "
                     f"{e['sa_hits']}/{e['sa_runs']} | {e['sa_time']} |\n")
    print(open(os.path.join(out, "summary.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
