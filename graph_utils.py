from __future__ import annotations

from dataclasses import dataclass
import random
from typing import List, Set, Tuple

Edge = Tuple[int, int]


@dataclass
class Graph:
    n: int
    edges: List[Edge]

    def __post_init__(self) -> None:
        self.adj: List[Set[int]] = [set() for _ in range(self.n)]
        for u, v in self.edges:
            if u == v:
                continue
            self.adj[u].add(v)
            self.adj[v].add(u)

    def degrees(self) -> List[int]:
        return [len(nei) for nei in self.adj]


def er_graph(n: int, p: float, rng: random.Random) -> Graph:
    edges: List[Edge] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < p:
                edges.append((i, j))
    return Graph(n=n, edges=edges)


def ba_graph(n: int, m: int, rng: random.Random) -> Graph:
    if m < 1 or m >= n:
        raise ValueError("BA parameter m must satisfy 1 <= m < n")

    edges: Set[Edge] = set()
    repeated: List[int] = []

    for i in range(m):
        for j in range(i + 1, m):
            edges.add((i, j))
            repeated.extend([i, j])

    for new_node in range(m, n):
        chosen: Set[int] = set()
        while len(chosen) < m:
            chosen.add(rng.choice(repeated or list(range(m))))
        for t in chosen:
            edges.add((min(new_node, t), max(new_node, t)))
            repeated.extend([new_node, t])
    return Graph(n=n, edges=list(edges))


def ws_graph(n: int, k: int, beta: float, rng: random.Random) -> Graph:
    if k % 2 != 0:
        raise ValueError("k must be even for WS graph")
    edges: Set[Edge] = set()
    half = k // 2
    for i in range(n):
        for d in range(1, half + 1):
            j = (i + d) % n
            edges.add((min(i, j), max(i, j)))

    rewired: Set[Edge] = set(edges)
    for (u, v) in list(edges):
        if rng.random() < beta:
            rewired.discard((u, v))
            w = rng.randrange(n)
            while w == u or (min(u, w), max(u, w)) in rewired:
                w = rng.randrange(n)
            rewired.add((min(u, w), max(u, w)))
    return Graph(n=n, edges=list(rewired))


def grid_graph(rows: int, cols: int) -> Graph:
    def idx(r: int, c: int) -> int:
        return r * cols + c

    edges: List[Edge] = []
    for r in range(rows):
        for c in range(cols):
            if r + 1 < rows:
                edges.append((idx(r, c), idx(r + 1, c)))
            if c + 1 < cols:
                edges.append((idx(r, c), idx(r, c + 1)))
    return Graph(n=rows * cols, edges=edges)


def generate_instance_groups(seed: int = 42, samples_per_group: int = 20):
    rng = random.Random(seed)
    groups = {
        "ER_sparse": [er_graph(40, 0.05, rng) for _ in range(samples_per_group)],
        "ER_dense": [er_graph(40, 0.20, rng) for _ in range(samples_per_group)],
        "BA_scale_free": [ba_graph(60, 2, rng) for _ in range(samples_per_group)],
        "WS_small_world": [ws_graph(60, 4, 0.30, rng) for _ in range(samples_per_group)],
        "Grid_structured": [grid_graph(8, 8) for _ in range(samples_per_group)],
    }
    return groups
