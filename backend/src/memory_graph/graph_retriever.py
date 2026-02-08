"""
GraphRetriever: Activation Energy algorithm for graph-based memory retrieval.

Implements concurrent multi-path graph explorations from seed nodes. 

> See GRAPH_RETRIEVAL.md for detailed algorithm documentation.

Usage::

    from neo4j import AsyncDriver
    from src.memory_graph.graph_retriever import GraphRetriever, SeedNode

    retriever = GraphRetriever(driver)  # driver is a long-lived AsyncDriver

    seeds = [
        SeedNode(node_id="N2007", score=0.85),
        SeedNode(node_id="N3012", score=0.72),
    ]
    query_tags = ["demand_forecasting", "stockout", "safety_stock"]

    async for result in retriever.explore(seeds, query_tags):
        print(result.seed_id, len(result.paths), result.max_depth_reached)
        for path in result.paths:
            for step in path.steps:
                print(f"  → {step.node_data['id']} (T={step.transfer_energy:.4f})")
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, LiteralString

from neo4j import AsyncDriver, AsyncManagedTransaction

# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_MAX_DEPTH: int = 5
DEFAULT_MIN_ACTIVATION: float = 0.005
DEFAULT_TAG_SIM_FLOOR: float = 0.15
DEFAULT_MAX_BRANCHES: int = 3
DEFAULT_MAX_RETRIES: int = 2
DATABASE_NAME: str = "memorygraph"


# ─── Cypher Queries ──────────────────────────────────────────────────────────

_SEED_QUERY: LiteralString = """
MATCH (n {id: $node_id})
RETURN properties(n) AS data, labels(n) AS labels
"""

_EXPAND_QUERY: LiteralString = """
UNWIND $frontier AS f
MATCH (current {id: f.node_id})
WITH current, f.node_id AS parent_id, f.activation AS activation,
     COUNT { (current)-[:RELATES]-() } AS degree

MATCH (current)-[r:RELATES]-(neighbor)
WHERE NOT neighbor.id IN $visited_ids

WITH parent_id, r, neighbor, activation, degree,
     coalesce(r.tags, []) AS eTags
WITH parent_id, r, neighbor, activation, degree, eTags,
     size([t IN eTags WHERE t IN $query_tags]) AS inter_count
WITH parent_id, r, neighbor, activation, degree, eTags, inter_count,
     CASE
         WHEN $query_tags_count = 0 THEN 1.0
         WHEN size(eTags) = 0       THEN $tag_sim_floor
         ELSE $tag_sim_floor
              + (1.0 - $tag_sim_floor)
              * toFloat(inter_count)
              / (size(eTags) + $query_tags_count - inter_count)
     END AS tag_sim

WITH parent_id, r, neighbor,
     (activation * coalesce(r.weight, 0.01) / sqrt(toFloat(degree))) * tag_sim
         AS transfer_energy

WHERE transfer_energy > $min_threshold

RETURN parent_id,
       properties(neighbor)  AS neighbor_data,
       labels(neighbor)       AS neighbor_labels,
       neighbor.id            AS neighbor_id,
       properties(r)          AS edge_data,
       transfer_energy
ORDER BY parent_id, transfer_energy DESC
"""


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SeedNode:
    """A starting point for graph exploration.

    Attributes:
        node_id: The ``id`` property of the Neo4j node (e.g. ``"N2007"``).
        score:   R(Mi) — hybrid similarity score from upstream vector search.
    """
    node_id: str
    score: float


@dataclass(slots=True)
class PathStep:
    """One hop in an explored path: the edge traversed and the node reached.

    Attributes:
        node_data:        All properties of the destination node as a dict.
        node_labels:      Neo4j labels on the destination node (e.g. ``["AgentAnswer"]``).
        edge_data:        All properties of the traversed RELATES edge as a dict.
        transfer_energy:  The computed T value for this hop.
    """
    node_data: dict[str, Any]
    node_labels: list[str]
    edge_data: dict[str, Any]
    transfer_energy: float


@dataclass(slots=True)
class ExploredPath:
    """A single complete path from seed outward through the graph.

    Attributes:
        steps: Ordered list of hops from seed outward.
        depth: Number of hops (== len(steps)).
        final_energy: Transfer energy at the last hop (lowest in the path).
    """
    steps: list[PathStep]
    depth: int
    final_energy: float


@dataclass(slots=True)
class ExplorationResult:
    """Complete output of one multi-path graph exploration from a single seed.

    Attributes:
        seed_id:            The starting node's ``id`` property.
        seed_score:         R(Mi) that was provided for the seed.
        seed_data:          All properties of the seed node (None if not found).
        seed_labels:        Neo4j labels on the seed node.
        paths:              List of complete paths discovered from this seed.
        max_depth_reached:  Deepest path length across all paths.
        terminated_reason:  Overall termination:
                            ``"complete"`` | ``"seed_not_found"``
    """
    seed_id: str
    seed_score: float
    seed_data: dict[str, Any] | None
    seed_labels: list[str]
    paths: list[ExploredPath] = field(default_factory=list)
    max_depth_reached: int = 0
    terminated_reason: str = ""


# ─── Internal frontier node (not exported) ────────────────────────────────────

@dataclass(slots=True)
class _FrontierNode:
    """Tracks one active branch during BFS expansion."""
    node_id: str
    activation: float
    path: list[PathStep]


# ─── GraphRetriever ──────────────────────────────────────────────────────────

class GraphRetriever:
    """Concurrent multi-path Activation-Energy graph explorer.

    Receives a shared, long-lived async Neo4j driver and exposes
    :meth:`explore` which launches independent, concurrent graph explorations
    from a list of seed nodes.  Results are yielded as each exploration
    completes (streamed via ``asyncio.as_completed``).

    Args:
        neo4j_driver:   An already-created ``AsyncDriver`` (shared app-wide).
        max_depth:      Maximum traversal hops per path (default ``5``).
        min_activation: Minimum Transfer Energy to continue a branch (default ``0.005``).
        tag_sim_floor:  Floored-Jaccard baseline (default ``0.15``).
        max_branches:   Max neighbors expanded per node per depth (default ``3``).
        database:       Neo4j database name (default ``"memorygraph"``).
    """

    __slots__ = (
        "_driver",
        "_max_depth",
        "_min_activation",
        "_tag_sim_floor",
        "_max_branches",
        "_database",
    )

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        *,
        max_depth: int = DEFAULT_MAX_DEPTH,
        min_activation: float = DEFAULT_MIN_ACTIVATION,
        tag_sim_floor: float = DEFAULT_TAG_SIM_FLOOR,
        max_branches: int = DEFAULT_MAX_BRANCHES,
        database: str = DATABASE_NAME,
    ) -> None:
        self._driver = neo4j_driver
        self._max_depth = max_depth
        self._min_activation = min_activation
        self._tag_sim_floor = tag_sim_floor
        self._max_branches = max_branches
        self._database = database

    # ── Public API ────────────────────────────────────────────────────────

    async def explore(
        self,
        seeds: list[SeedNode],
        query_tags: list[str],
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """Run concurrent multi-path graph explorations from all seeds.

        Results are yielded **as each exploration finishes** — an early
        finisher is surfaced immediately while others are still running.

        Args:
            seeds:       List of ``SeedNode`` (node_id + score).
            query_tags:  Tags extracted from the user query.
            max_retries: Per-exploration retry limit on transient failure.

        Yields:
            ``ExplorationResult`` for each completed seed exploration.
        """
        if not seeds:
            return

        tasks: list[asyncio.Task[ExplorationResult]] = [
            asyncio.create_task(
                self._explore_with_retry(seed, query_tags, max_retries),
                name=f"graph-explore-{seed.node_id}",
            )
            for seed in seeds
        ]

        try:
            for future in asyncio.as_completed(tasks):
                try:
                    result: ExplorationResult = await future
                    yield result
                except Exception:
                    print("Graph exploration failed after all retries")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Internal: retry wrapper ───────────────────────────────────────────

    async def _explore_with_retry(
        self,
        seed: SeedNode,
        query_tags: list[str],
        max_retries: int,
    ) -> ExplorationResult:
        """Run a single exploration with automatic retry + exponential backoff."""
        last_exc: BaseException | None = None
        for attempt in range(max_retries + 1):
            try:
                return await self._explore_single(seed, query_tags)
            except Exception as exc:
                last_exc = exc
                print(
                    "Exploration from seed %s — attempt %d/%d failed: %s",
                    seed.node_id,
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.05 * (2 ** attempt))
        raise last_exc  # type: ignore[misc]

    # ── Internal: single multi-path exploration ───────────────────────────

    async def _explore_single(
        self,
        seed: SeedNode,
        query_tags: list[str],
    ) -> ExplorationResult:
        """Execute one full multi-path BFS exploration from *seed*.

        Opens its own ``AsyncSession`` (lightweight, from the driver pool)
        and runs inside ``session.execute_read`` for automatic transient-error
        retries and consistent read snapshot.
        """
        max_depth = self._max_depth
        min_activation = self._min_activation
        tag_sim_floor = self._tag_sim_floor
        max_branches = self._max_branches
        query_tags_count = len(query_tags)

        async def _run(tx: AsyncManagedTransaction) -> ExplorationResult:
            # ── 1. Fetch seed node ────────────────────────────────────
            seed_cursor = await tx.run(_SEED_QUERY, node_id=seed.node_id)
            seed_record = await seed_cursor.single()

            if seed_record is None:
                print("Seed node %s not found in graph", seed.node_id)
                return ExplorationResult(
                    seed_id=seed.node_id,
                    seed_score=seed.score,
                    seed_data=None,
                    seed_labels=[],
                    terminated_reason="seed_not_found",
                )

            seed_data: dict[str, Any] = dict(seed_record["data"])
            seed_labels: list[str] = list(seed_record["labels"])

            # ── 2. BFS multi-path traversal ───────────────────────────
            frontier: list[_FrontierNode] = [
                _FrontierNode(node_id=seed.node_id, activation=seed.score, path=[])
            ]
            visited: set[str] = {seed.node_id}
            completed_paths: list[ExploredPath] = []

            for _depth in range(max_depth):
                if not frontier:
                    break

                # Build Cypher parameter: list of {node_id, activation}
                frontier_param = [
                    {"node_id": f.node_id, "activation": f.activation}
                    for f in frontier
                ]

                expand_cursor = await tx.run(
                    _EXPAND_QUERY,
                    frontier=frontier_param,
                    visited_ids=list(visited),
                    query_tags=query_tags,
                    query_tags_count=query_tags_count,
                    tag_sim_floor=tag_sim_floor,
                    min_threshold=min_activation,
                )
                records = [record async for record in expand_cursor]

                # Group candidates by parent_id (already sorted by T desc)
                candidates_by_parent: dict[str, list[Any]] = defaultdict(list)
                for rec in records:
                    candidates_by_parent[rec["parent_id"]].append(rec)

                # Build next frontier + collect completed paths
                next_frontier: list[_FrontierNode] = []
                newly_visited: set[str] = set()

                for f_node in frontier:
                    candidates = candidates_by_parent.get(f_node.node_id, [])
                    branch_count = 0

                    for cand in candidates:
                        if branch_count >= max_branches:
                            break
                        neighbor_id: str = cand["neighbor_id"]
                        # Avoid two frontier nodes at the same depth
                        # both expanding to the same neighbor.
                        if neighbor_id in newly_visited:
                            continue
                        branch_count += 1
                        newly_visited.add(neighbor_id)

                        step = PathStep(
                            node_data=dict(cand["neighbor_data"]),
                            node_labels=list(cand["neighbor_labels"]),
                            edge_data=dict(cand["edge_data"]),
                            transfer_energy=float(cand["transfer_energy"]),
                        )
                        extended_path = f_node.path + [step]
                        next_frontier.append(
                            _FrontierNode(
                                node_id=neighbor_id,
                                activation=float(cand["transfer_energy"]),
                                path=extended_path,
                            )
                        )

                    # If this frontier node produced no branches, its path
                    # is complete (dead end or all below threshold).
                    if branch_count == 0 and f_node.path:
                        completed_paths.append(
                            ExploredPath(
                                steps=f_node.path,
                                depth=len(f_node.path),
                                final_energy=f_node.path[-1].transfer_energy,
                            )
                        )

                visited.update(newly_visited)
                frontier = next_frontier

            # Remaining frontier nodes hit MAX_DEPTH, their paths are complete.
            for f_node in frontier:
                if f_node.path:
                    completed_paths.append(
                        ExploredPath(
                            steps=f_node.path,
                            depth=len(f_node.path),
                            final_energy=f_node.path[-1].transfer_energy,
                        )
                    )

            max_depth_reached = (
                max((p.depth for p in completed_paths), default=0)
            )

            return ExplorationResult(
                seed_id=seed.node_id,
                seed_score=seed.score,
                seed_data=seed_data,
                seed_labels=seed_labels,
                paths=completed_paths,
                max_depth_reached=max_depth_reached,
                terminated_reason="complete",
            )

        # Open a dedicated session for this exploration.
        async with self._driver.session(database=self._database) as session:
            return await session.execute_read(_run)
