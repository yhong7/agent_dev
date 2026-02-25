from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from graph_utils import Graph


@dataclass
class RunResult:
    cover: Set[int]
    cover_size: int
    elapsed: float
    best_trace: List[int]
    iter_to_best: int


# ---------- utilities ----------
def uncovered_edges(graph: Graph, cover: Set[int]) -> int:
    return sum(1 for u, v in graph.edges if u not in cover and v not in cover)


def greedy_repair_cover(graph: Graph, cover: Set[int]) -> Set[int]:
    cover = set(cover)
    for u, v in graph.edges:
        if u not in cover and v not in cover:
            du, dv = len(graph.adj[u]), len(graph.adj[v])
            cover.add(u if du >= dv else v)

    # cheap one-pass pruning
    for v in list(cover):
        cover.remove(v)
        if uncovered_edges(graph, cover) > 0:
            cover.add(v)
    return cover


def score(graph: Graph, cover: Set[int], penalty: float = 4.0) -> float:
    return len(cover) + penalty * uncovered_edges(graph, cover)


# ---------- SA ----------
def simulated_annealing(graph: Graph, seed: int, max_iter: int = 300) -> RunResult:
    rng = random.Random(seed)
    start = time.perf_counter()

    current = greedy_repair_cover(graph, set(range(graph.n)))
    best = set(current)
    current_score = score(graph, current)
    best_score = current_score

    t0, t_end = 3.0, 0.01
    trace: List[int] = []
    iter_to_best = 0

    for it in range(1, max_iter + 1):
        temp = t0 * ((t_end / t0) ** (it / max_iter))
        candidate = set(current)

        if rng.random() < 0.5 and candidate:
            candidate.remove(rng.choice(tuple(candidate)))
        else:
            candidate.add(rng.randrange(graph.n))

        cand_score = score(graph, candidate)
        delta = cand_score - current_score
        if delta <= 0 or rng.random() < math.exp(-delta / max(temp, 1e-9)):
            current = candidate
            current_score = cand_score

        repaired = greedy_repair_cover(graph, current)
        repaired_score = score(graph, repaired)
        if repaired_score <= current_score:
            current = repaired
            current_score = repaired_score

        if current_score < best_score:
            best, best_score, iter_to_best = set(current), current_score, it

        trace.append(len(best))

    elapsed = time.perf_counter() - start
    best = greedy_repair_cover(graph, best)
    return RunResult(best, len(best), elapsed, trace, iter_to_best)


# ---------- GA ----------
def _random_cover(graph: Graph, rng: random.Random) -> Set[int]:
    s = {i for i in range(graph.n) if rng.random() < 0.5}
    return greedy_repair_cover(graph, s)


def genetic_algorithm(
    graph: Graph,
    seed: int,
    population_size: int = 12,
    generations: int = 30,
    mutation_rate: float = 0.08,
) -> RunResult:
    rng = random.Random(seed)
    start = time.perf_counter()

    population = [_random_cover(graph, rng) for _ in range(population_size)]
    trace: List[int] = []

    best = min(population, key=lambda c: len(c))
    best_size = len(best)
    iter_to_best = 0

    def tournament(pop: Sequence[Set[int]], k: int = 3) -> Set[int]:
        cand = rng.sample(pop, k)
        return min(cand, key=len)

    for g in range(1, generations + 1):
        new_pop: List[Set[int]] = []
        elite = min(population, key=len)
        new_pop.append(set(elite))

        while len(new_pop) < population_size:
            p1, p2 = tournament(population), tournament(population)
            child = set()
            for v in range(graph.n):
                in1, in2 = v in p1, v in p2
                if in1 == in2:
                    if in1:
                        child.add(v)
                else:
                    if rng.random() < 0.5:
                        child.add(v)

            for v in range(graph.n):
                if rng.random() < mutation_rate:
                    if v in child:
                        child.remove(v)
                    else:
                        child.add(v)

            child = greedy_repair_cover(graph, child)
            new_pop.append(child)

        population = new_pop
        candidate = min(population, key=len)
        csize = len(candidate)
        if csize < best_size:
            best, best_size, iter_to_best = set(candidate), csize, g
        trace.append(best_size)

    elapsed = time.perf_counter() - start
    return RunResult(best, best_size, elapsed, trace, iter_to_best)


# ---------- ACO ----------
def ant_colony(
    graph: Graph,
    seed: int,
    ants: int = 8,
    iterations: int = 20,
    alpha: float = 1.0,
    beta: float = 2.0,
    rho: float = 0.2,
) -> RunResult:
    rng = random.Random(seed)
    start = time.perf_counter()

    n = graph.n
    deg = graph.degrees()
    heuristic = [d + 1e-6 for d in deg]
    pheromone = [1.0 for _ in range(n)]

    best_cover = set(range(n))
    best_size = n
    iter_to_best = 0
    trace: List[int] = []

    for it in range(1, iterations + 1):
        iteration_best: Tuple[int, Set[int]] = (10**9, set())

        for _ in range(ants):
            uncovered = set(graph.edges)
            cover: Set[int] = set()

            while uncovered:
                weights = []
                verts = []
                for v in range(n):
                    if v in cover:
                        continue
                    contrib = 0
                    for u in graph.adj[v]:
                        e = (min(u, v), max(u, v))
                        if e in uncovered:
                            contrib += 1
                    if contrib == 0:
                        continue
                    w = (pheromone[v] ** alpha) * ((heuristic[v] * contrib) ** beta)
                    verts.append(v)
                    weights.append(w)

                if not verts:
                    break
                chosen = rng.choices(verts, weights=weights, k=1)[0]
                cover.add(chosen)

                to_remove = []
                for u, v in uncovered:
                    if chosen in (u, v):
                        to_remove.append((u, v))
                for e in to_remove:
                    uncovered.discard(e)

            cover = greedy_repair_cover(graph, cover)
            csize = len(cover)
            if csize < iteration_best[0]:
                iteration_best = (csize, cover)

        for v in range(n):
            pheromone[v] *= (1 - rho)

        size_i, cover_i = iteration_best
        for v in cover_i:
            pheromone[v] += 1.0 / max(size_i, 1)

        if size_i < best_size:
            best_size, best_cover, iter_to_best = size_i, set(cover_i), it
        trace.append(best_size)

    elapsed = time.perf_counter() - start
    return RunResult(best_cover, best_size, elapsed, trace, iter_to_best)


ALGORITHMS = {
    "SA": simulated_annealing,
    "GA": genetic_algorithm,
    "ACO": ant_colony,
}
