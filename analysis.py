from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from typing import Dict, List, Tuple

RESULT_DIR = "result"

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float_rows(rows: List[Dict[str, str]]) -> List[Dict]:
    out = []
    for r in rows:
        row = dict(r)
        for k in ["time_mean", "time_var", "cover_mean", "cover_var", "gap_mean", "gap_var", "iter_best_mean", "iter_best_var"]:
            if k in row:
                row[k] = float(row[k])
        out.append(row)
    return out


def _write_text_report(summary: List[Dict], raw_rows: List[Dict[str, str]]) -> None:
    path = os.path.join(RESULT_DIR, "report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Vertex Cover 元启发算法实验摘要\n")
        f.write("=" * 40 + "\n")
        for r in summary:
            f.write(
                f"{r['group']} | {r['algorithm']} | time_mean={r['time_mean']:.4f}s | "
                f"cover_mean={r['cover_mean']:.2f} | gap_mean={r['gap_mean']:.4f} | "
                f"iter_best_mean={r['iter_best_mean']:.2f}\n"
            )

        f.write("\nEmpirical runtime trend slope (log-log vs edge count):\n")
        bucket: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        for r in raw_rows:
            bucket[r["algorithm"]].append((float(r["m"]), float(r["time_s"])))
        for algo, pts in bucket.items():
            logs = [(math.log(max(x, 1)), math.log(max(y, 1e-9))) for x, y in pts]
            x_mean = sum(x for x, _ in logs) / len(logs)
            y_mean = sum(y for _, y in logs) / len(logs)
            num = sum((x - x_mean) * (y - y_mean) for x, y in logs)
            den = sum((x - x_mean) ** 2 for x, _ in logs) + 1e-9
            b = num / den
            f.write(f"- {algo}: slope={b:.3f}\n")


def _svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">' \
           '<style>text{font-family:Arial,sans-serif;font-size:12px}.title{font-size:16px;font-weight:bold}</style>'


def _save_svg(path: str, body: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(body + ["</svg>"]))


def _plot_group_bars_svg(summary: List[Dict], metric: str, ylabel: str, filename: str) -> None:
    groups = sorted({r["group"] for r in summary})
    algos = sorted({r["algorithm"] for r in summary})
    colors = {"SA": "#4e79a7", "GA": "#59a14f", "ACO": "#e15759"}

    width, height = 980, 420
    margin_l, margin_r, margin_t, margin_b = 80, 20, 45, 85
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    max_val = max(r[metric] for r in summary) if summary else 1.0
    max_val = max(max_val, 1e-9)

    elems = [_svg_header(width, height)]
    elems.append(f'<text x="{width//2}" y="24" text-anchor="middle" class="title">{ylabel} by instance group</text>')

    # axes
    x0, y0 = margin_l, height - margin_b
    elems.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{margin_t}" stroke="black"/>')
    elems.append(f'<line x1="{x0}" y1="{y0}" x2="{width-margin_r}" y2="{y0}" stroke="black"/>')

    group_w = plot_w / max(len(groups), 1)
    bar_w = group_w / (len(algos) + 1)

    # y ticks
    for i in range(6):
        v = max_val * i / 5
        y = y0 - (v / max_val) * plot_h
        elems.append(f'<line x1="{x0-4}" y1="{y:.1f}" x2="{x0}" y2="{y:.1f}" stroke="black"/>')
        elems.append(f'<text x="{x0-8}" y="{y+4:.1f}" text-anchor="end">{v:.2f}</text>')

    # bars
    for gi, g in enumerate(groups):
        gx = x0 + gi * group_w
        for ai, algo in enumerate(algos):
            row = next(r for r in summary if r["group"] == g and r["algorithm"] == algo)
            val = row[metric]
            h = (val / max_val) * plot_h
            x = gx + (ai + 0.5) * bar_w
            y = y0 - h
            elems.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.8:.1f}" height="{h:.1f}" fill="{colors.get(algo, "#777")}"/>')

        elems.append(f'<text x="{gx + group_w/2:.1f}" y="{y0+20}" text-anchor="middle" transform="rotate(20 {gx + group_w/2:.1f},{y0+20})">{g}</text>')

    # legend
    lx = width - margin_r - 170
    ly = margin_t + 10
    for i, algo in enumerate(algos):
        yy = ly + i * 20
        elems.append(f'<rect x="{lx}" y="{yy-10}" width="14" height="14" fill="{colors.get(algo, "#777")}"/>')
        elems.append(f'<text x="{lx+20}" y="{yy+1}">{algo}</text>')

    elems.append(f'<text x="20" y="{margin_t + plot_h/2:.1f}" transform="rotate(-90 20,{margin_t + plot_h/2:.1f})" text-anchor="middle">{ylabel}</text>')
    _save_svg(os.path.join(RESULT_DIR, filename), elems)


def _plot_trend_svg(raw_rows: List[Dict[str, str]]) -> None:
    bucket: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for r in raw_rows:
        bucket[r["algorithm"]].append((float(r["m"]), float(r["time_s"])))

    width, height = 880, 460
    margin_l, margin_r, margin_t, margin_b = 70, 25, 45, 60
    x0, y0 = margin_l, height - margin_b
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    colors = {"SA": "#4e79a7", "GA": "#59a14f", "ACO": "#e15759"}

    all_x = [x for pts in bucket.values() for x, _ in pts]
    all_y = [y for pts in bucket.values() for _, y in pts]
    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y), max(all_y)
    ymin, ymax = min(ymin, 0.0), max(ymax, 1e-9)

    def sx(x: float) -> float:
        return x0 + (x - xmin) / (xmax - xmin + 1e-9) * plot_w

    def sy(y: float) -> float:
        return y0 - (y - ymin) / (ymax - ymin + 1e-9) * plot_h

    elems = [_svg_header(width, height)]
    elems.append('<text x="440" y="24" text-anchor="middle" class="title">Empirical runtime growth trend</text>')
    elems.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{margin_t}" stroke="black"/>')
    elems.append(f'<line x1="{x0}" y1="{y0}" x2="{width-margin_r}" y2="{y0}" stroke="black"/>')

    for algo, pts in bucket.items():
        for x, y in pts:
            elems.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.6" fill="{colors.get(algo, "#777")}" opacity="0.55"/>')

    # legend
    lx, ly = width - margin_r - 120, margin_t + 10
    for i, algo in enumerate(sorted(bucket.keys())):
        yy = ly + i * 20
        elems.append(f'<rect x="{lx}" y="{yy-10}" width="14" height="14" fill="{colors.get(algo, "#777")}"/>')
        elems.append(f'<text x="{lx+20}" y="{yy+1}">{algo}</text>')

    elems.append(f'<text x="{x0 + plot_w/2:.1f}" y="{height-20}" text-anchor="middle">Edge count m</text>')
    elems.append(f'<text x="20" y="{margin_t + plot_h/2:.1f}" transform="rotate(-90 20,{margin_t + plot_h/2:.1f})" text-anchor="middle">Runtime (s)</text>')

    _save_svg(os.path.join(RESULT_DIR, "trend_time_vs_edges.svg"), elems)


def plot_group_bars(summary: List[Dict]) -> None:
    groups = sorted({r["group"] for r in summary})
    algos = sorted({r["algorithm"] for r in summary})

    metrics = [
        ("time_mean", "Runtime (s)"),
        ("cover_mean", "Cover size"),
        ("gap_mean", "Gap to lower bound"),
    ]

    for metric, ylabel in metrics:
        plt.figure(figsize=(10, 4))
        x = list(range(len(groups)))
        width = 0.22
        for i, algo in enumerate(algos):
            vals = []
            for g in groups:
                row = next(r for r in summary if r["group"] == g and r["algorithm"] == algo)
                vals.append(row[metric])
            shift = [xi + (i - 1) * width for xi in x]
            plt.bar(shift, vals, width=width, label=algo)

        plt.xticks(x, groups, rotation=20)
        plt.ylabel(ylabel)
        plt.title(f"{ylabel} by instance group")
        plt.legend()
        plt.tight_layout()
        out_path = os.path.join(RESULT_DIR, f"bar_{metric}.png")
        plt.savefig(out_path, dpi=160)
        plt.close()


def plot_complexity_trend(raw_rows: List[Dict[str, str]]) -> None:
    bucket: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for r in raw_rows:
        bucket[r["algorithm"]].append((float(r["m"]), float(r["time_s"])))

    plt.figure(figsize=(7, 5))
    for algo, pts in bucket.items():
        pts.sort(key=lambda x: x[0])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        plt.scatter(xs, ys, s=10, alpha=0.35, label=algo)

        logs = [(math.log(max(x, 1)), math.log(max(y, 1e-9))) for x, y in pts]
        x_mean = sum(x for x, _ in logs) / len(logs)
        y_mean = sum(y for _, y in logs) / len(logs)
        num = sum((x - x_mean) * (y - y_mean) for x, y in logs)
        den = sum((x - x_mean) ** 2 for x, _ in logs) + 1e-9
        b = num / den
        a = y_mean - b * x_mean
        x_line = sorted(set(xs))
        y_line = [math.exp(a) * (x ** b) for x in x_line]
        plt.plot(x_line, y_line, linewidth=2)

    plt.xlabel("Edge count m")
    plt.ylabel("Runtime (s)")
    plt.title("Empirical runtime growth trend")
    plt.legend()
    plt.tight_layout()
    out_path = os.path.join(RESULT_DIR, "trend_time_vs_edges.png")
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    summary_rows = to_float_rows(read_csv(os.path.join(RESULT_DIR, "summary.csv")))
    raw_rows = read_csv(os.path.join(RESULT_DIR, "raw_runs.csv"))
    _write_text_report(summary_rows, raw_rows)

    if plt is None:
        _plot_group_bars_svg(summary_rows, "time_mean", "Runtime (s)", "bar_time_mean.svg")
        _plot_group_bars_svg(summary_rows, "cover_mean", "Cover size", "bar_cover_mean.svg")
        _plot_group_bars_svg(summary_rows, "gap_mean", "Gap to lower bound", "bar_gap_mean.svg")
        _plot_trend_svg(raw_rows)
        print("matplotlib not installed; generated SVG charts and text report in result/")
        return

    plot_group_bars(summary_rows)
    plot_complexity_trend(raw_rows)
    print("Saved plots into result/")


if __name__ == "__main__":
    main()
