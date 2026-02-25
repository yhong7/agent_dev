from __future__ import annotations

import csv
import math
import os
import struct
import zlib
from collections import defaultdict
from typing import Dict, List, Tuple

RESULT_DIR = "result"

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


# ---------- CSV helpers ----------
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


# ---------- text report ----------
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


# ---------- lightweight PNG fallback (no external deps) ----------
class SimpleCanvas:
    def __init__(self, w: int, h: int, bg=(255, 255, 255)):
        self.w = w
        self.h = h
        self.px = [[bg for _ in range(w)] for _ in range(h)]

    def set(self, x: int, y: int, c=(0, 0, 0)):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def line(self, x1: int, y1: int, x2: int, y2: int, c=(0, 0, 0)):
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x, y = x1, y1
        while True:
            self.set(x, y, c)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def rect(self, x: int, y: int, w: int, h: int, c=(0, 0, 0)):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def circle(self, cx: int, cy: int, r: int, c=(0, 0, 0)):
        rr = r * r
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= rr:
                    self.set(x, y, c)

    def save_png(self, path: str):
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        raw = bytearray()
        for row in self.px:
            raw.append(0)
            for r, g, b in row:
                raw.extend((r, g, b))

        ihdr = struct.pack("!IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(data)


def _draw_fallback_bars(summary: List[Dict], metric: str, out_name: str):
    groups = sorted({r["group"] for r in summary})
    algos = sorted({r["algorithm"] for r in summary})
    colors = {"SA": (78, 121, 167), "GA": (89, 161, 79), "ACO": (225, 87, 89)}

    w, h = 980, 420
    ml, mr, mt, mb = 70, 20, 20, 45
    pw, ph = w - ml - mr, h - mt - mb
    c = SimpleCanvas(w, h)
    c.line(ml, h - mb, ml, mt, (0, 0, 0))
    c.line(ml, h - mb, w - mr, h - mb, (0, 0, 0))

    vmax = max(r[metric] for r in summary) if summary else 1.0
    vmax = max(vmax, 1e-9)
    gw = pw / max(len(groups), 1)
    bw = max(int(gw / (len(algos) + 1) * 0.8), 3)

    for gi, g in enumerate(groups):
        gx = ml + gi * gw
        for ai, algo in enumerate(algos):
            row = next(r for r in summary if r["group"] == g and r["algorithm"] == algo)
            val = row[metric]
            bh = int((val / vmax) * ph)
            x = int(gx + (ai + 0.5) * gw / (len(algos) + 1))
            y = h - mb - bh
            c.rect(x, y, bw, bh, colors.get(algo, (120, 120, 120)))

    c.save_png(os.path.join(RESULT_DIR, out_name))


def _draw_fallback_scatter(raw_rows: List[Dict[str, str]], out_name: str):
    bucket: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for r in raw_rows:
        bucket[r["algorithm"]].append((float(r["m"]), float(r["time_s"])))

    colors = {"SA": (78, 121, 167), "GA": (89, 161, 79), "ACO": (225, 87, 89)}
    w, h = 880, 460
    ml, mr, mt, mb = 70, 25, 20, 50
    pw, ph = w - ml - mr, h - mt - mb
    c = SimpleCanvas(w, h)
    c.line(ml, h - mb, ml, mt, (0, 0, 0))
    c.line(ml, h - mb, w - mr, h - mb, (0, 0, 0))

    xs = [x for pts in bucket.values() for x, _ in pts]
    ys = [y for pts in bucket.values() for _, y in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    ymin = min(ymin, 0.0)
    ymax = max(ymax, 1e-9)

    def sx(x: float) -> int:
        return int(ml + (x - xmin) / (xmax - xmin + 1e-9) * pw)

    def sy(y: float) -> int:
        return int(h - mb - (y - ymin) / (ymax - ymin + 1e-9) * ph)

    for algo, pts in bucket.items():
        for x, y in pts:
            c.circle(sx(x), sy(y), 2, colors.get(algo, (100, 100, 100)))

    c.save_png(os.path.join(RESULT_DIR, out_name))


# ---------- matplotlib path ----------
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
        _draw_fallback_bars(summary_rows, "time_mean", "bar_time_mean.png")
        _draw_fallback_bars(summary_rows, "cover_mean", "bar_cover_mean.png")
        _draw_fallback_bars(summary_rows, "gap_mean", "bar_gap_mean.png")
        _draw_fallback_scatter(raw_rows, "trend_time_vs_edges.png")
        print("matplotlib not installed; generated PNG charts via built-in fallback in result/")
        return

    plot_group_bars(summary_rows)
    plot_complexity_trend(raw_rows)
    print("Saved plots into result/")


if __name__ == "__main__":
    main()
