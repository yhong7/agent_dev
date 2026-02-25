from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
from collections import defaultdict
from typing import Dict, List

from algorithms import ALGORITHMS
from graph_utils import Graph, generate_instance_groups

RESULT_DIR = "result"


def _lower_bound_matching(graph: Graph) -> int:
    matched = set()
    m = 0
    for u, v in graph.edges:
        if u not in matched and v not in matched:
            matched.add(u)
            matched.add(v)
            m += 1
    return m


def run_experiments(master_seed: int = 2025, samples_per_group: int = 20, runs: int = 5) -> None:
    os.makedirs(RESULT_DIR, exist_ok=True)
    groups = generate_instance_groups(seed=master_seed, samples_per_group=samples_per_group)

    raw_rows: List[Dict] = []

    for gname, instances in groups.items():
        for idx, graph in enumerate(instances):
            lb = _lower_bound_matching(graph)
            for algo_name, algo in ALGORITHMS.items():
                for rep in range(runs):
                    seed = random.Random((master_seed, gname, idx, algo_name, rep).__hash__()).randrange(10**9)
                    res = algo(graph, seed=seed)
                    raw_rows.append(
                        {
                            "group": gname,
                            "instance": idx,
                            "algorithm": algo_name,
                            "repeat": rep,
                            "n": graph.n,
                            "m": len(graph.edges),
                            "time_s": res.elapsed,
                            "cover_size": res.cover_size,
                            "lower_bound": lb,
                            "gap_to_lb": (res.cover_size - lb) / max(lb, 1),
                            "iter_to_best": res.iter_to_best,
                            "final_best": res.best_trace[-1] if res.best_trace else res.cover_size,
                        }
                    )

    raw_path = os.path.join(RESULT_DIR, "raw_runs.csv")
    with open(raw_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        writer.writeheader()
        writer.writerows(raw_rows)

    summary = summarize(raw_rows)
    summary_path = os.path.join(RESULT_DIR, "summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print(f"Saved: {raw_path}")
    print(f"Saved: {summary_path}")


def summarize(rows: List[Dict]) -> List[Dict]:
    bucket: Dict[tuple, List[Dict]] = defaultdict(list)
    for r in rows:
        key = (r["group"], r["algorithm"])
        bucket[key].append(r)

    out = []
    for (group, algo), vals in sorted(bucket.items()):
        times = [v["time_s"] for v in vals]
        covers = [v["cover_size"] for v in vals]
        gaps = [v["gap_to_lb"] for v in vals]
        iters = [v["iter_to_best"] for v in vals]
        out.append(
            {
                "group": group,
                "algorithm": algo,
                "samples": len(vals),
                "time_mean": statistics.mean(times),
                "time_var": statistics.pvariance(times),
                "cover_mean": statistics.mean(covers),
                "cover_var": statistics.pvariance(covers),
                "gap_mean": statistics.mean(gaps),
                "gap_var": statistics.pvariance(gaps),
                "iter_best_mean": statistics.mean(iters),
                "iter_best_var": statistics.pvariance(iters),
            }
        )
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--samples-per-group", type=int, default=20)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    run_experiments(master_seed=args.seed, samples_per_group=args.samples_per_group, runs=args.runs)
