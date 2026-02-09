# Plan: Refactoring, Parsing, and Testing for GraphRetriever

This document is the execution plan for refactoring, output parsing, and testing of the Activation Energy GraphRetriever algorithm. It is organized as a set of detailed tasks that can be assigned independently and executed in order.

## Executive Summary
We will refactor the current GraphRetriever into testable components while preserving the exact algorithmic behavior. We will introduce explicit dataclasses for nodes, edges, paths, and results to support multiple output formats: React/D3 visualization, LLM-friendly context, and manual debugging (node ID lists). We will then build a multi-layer test suite that verifies (1) math, (2) Cypher expansion correctness, (3) BFS traversal logic correctness, and (4) end-to-end reasonableness on controlled dummy data.

The work should be executed in this order:
1. Data model + output parsing definitions.
2. Refactoring into testable components that use the new dataclasses.
3. Tests for math, Cypher expansion, BFS state, and logic reasonableness.

## 1. Refactoring Plan: Decompose GraphRetriever Without Changing Logic

**Goal:** Make the current GraphRetriever implementation testable by isolating Cypher execution, BFS state, and output formatting. The algorithmic logic must remain identical to the current implementation in graph_retriever.py.

### 1.1. Files and responsibilities

Create or update the following logical units (exact file layout up to the developer):

1) **Connector: Neo4j data access layer**
    - Responsibility: execute Cypher only. No BFS logic, no filtering.
    - Inputs: already structured parameters (frontier, visited, query tags).
    - Outputs: typed candidate records (already parsed into dataclasses).
    - Required methods:
      - `fetch_seed(node_id: str) -> SeedFetchResult`
      - `expand_frontier(frontier: list[FrontierInput], visited_ids: set[str], query_tags: list[str]) -> list[ExpansionCandidate]`
    - Notes:
      - Use `AsyncSession.execute_read()` and `AsyncManagedTransaction.run()` exactly as the current code does..
      - Preserve current Cypher queries. Only move them into the connector.

2) **Traversal state: BFS logic layer**
    - Responsibility: manage BFS state, visited tracking, candidate filtering, max branches selection, and path completion.
    - Inputs: current frontier nodes, expansion candidates grouped by parent, config values.
    - Outputs: next frontier, completed paths, updated visited set, termination reason.
    - Required methods:
      - `build_frontier_inputs(frontier: list[FrontierNode]) -> list[FrontierInput]`
      - `select_next_frontier(candidates_by_parent: dict[str, list[ExpansionCandidate]]) -> FrontierUpdateResult`
      - `finalize_remaining(frontier: list[FrontierNode]) -> list[GraphPath]`
    - Notes:
      - Preserve the same behavior for: max branches per parent, skip neighbors already claimed at the same depth, and record completed paths when a frontier node yields zero branches.

3) **Orchestrator: GraphRetriever**
    - Responsibility: create neo4j sessions, run the depth loop, call connector, call traversal state, and collect results.
    - Behavior: same as current `explore` and `_explore_single` with retries, cancellation, and `asyncio.as_completed` streaming.
    - Outputs: structured `RetrievalResult` objects.

### 1.2. Configuration and initialization

Make GraphRetriever as simple as possible to initialize:
- One required config object: `GraphRetrieverConfig(max_depth, min_activation, tag_sim_floor, max_branches, max_retries, database)`.
- No backward compatibility is needed. Remove legacy init signatures and enforce a single, clear constructor.

### 1.3. Data flow (must preserve logic)

1) `explore()` creates tasks and yields results as they finish (as today).
2) `_explore_single()` opens a session, runs a managed read transaction.
3) Seed fetch: if not found, return the same response as today (`seed_not_found`).
4) For each depth:
    - Build frontier inputs: node_id + activation.
    - Expand via a single Cypher call.
    - Group by parent_id, take top candidates, deduplicate per depth.
    - Update visited and frontier.
    - If a branch yields zero candidates, complete that path.
5) At max depth: complete any remaining frontier paths.
6) Return a final `RetrievalResult` with paths and `max_depth_reached`.

### 1.4. Internal refactor checklist

- Preserve every query, parameter name, and logic detail.
- Preserve `sqrt(degree)` normalization and `tag_sim_floor` logic in Cypher.
- Preserve the definition of `completed_paths` and `max_depth_reached`.
- Preserve retry behavior and exponential backoff.
- Avoid changing data returned from Cypher; only parse it into dataclasses.
- Ensure all async behavior is preserved; no blocking calls.

## 2. Output Parsing & Data Structures Plan

**Goal:** Produce a single internal representation that can be exported for (A) React D3 graph rendering, (B) LLM context strings, and (C) manual verification.

### 2.1. Dataclasses (internal model)

Define these with standard `dataclasses` or `pydantic` models and keep them JSON-serializable. Add these to models.py in the same module as GraphRetriever. If choosing `pydantic`, the developer must include a short rationale (validation, serialization, or type coercion needs).

1) **SeedInput**
    - `node_id: str`
    - `score: float`
    - Meaning: input from vector search; `score` is $R(M_i)$ for the seed.

2) **SeedFetchResult**
    - `node: GraphNode | None`
    - `labels: list[str]`
    - `found: bool`
    - Meaning: output of the seed fetch query; `found` false means `seed_not_found`.

3) **GraphNode**
    - `id: str`
    - `labels: list[str]`
    - `properties: dict[str, Any]`
    - Meaning: a node as returned by Neo4j with stable id and metadata.

4) **GraphEdge**
    - `source_id: str`
    - `target_id: str`
    - `type: str` (always “RELATES” for now, but keep field for future)
    - `properties: dict[str, Any]`
    - `weight: float | None`
    - `tags: list[str]`
    - Meaning: directed representation of an undirected RELATES edge; source/target are chosen by traversal direction.

5) **FrontierNode**
    - `node_id: str`
    - `activation: float`
    - `path: GraphPath`
    - Meaning: current BFS frontier element; `activation` is the transfer energy from the previous hop.

6) **GraphStep** 
    - `from_node: GraphNode`
    - `edge: GraphEdge`
    - `to_node: GraphNode`
    - `transfer_energy: float`
    - Meaning: one directed hop in the path; `from_node` to `to_node` via `edge` with computed transfer energy.

7) **GraphPath**
    - `steps: list[GraphStep]`
    - `max_transfer_energy: float`
    - `min_transfer_energy: float`
    - Meaning: a complete path from seed to a leaf. The seed is inferred as `steps[0].from_node`.

8) **ExpansionCandidate**
    - `parent_id: str`
    - `neighbor_node: GraphNode`
    - `edge: GraphEdge`
    - `transfer_energy: float`
    - Meaning: a potential next hop produced by the Cypher expansion before top-k selection.

9) **RetrievalResult**
    - `seed: SeedInput`
    - `seed_node: GraphNode | None`
    - `paths: list[GraphPath]`
    - `max_depth_reached: int`
    - `terminated_reason: str`
    - Meaning: final output per seed; includes structured paths and termination status.

### 2.2. Parsing outputs from Neo4j driver

Use `AsyncManagedTransaction.run()` and access `Record` by key exactly as in the current implementation. The mapping should be explicit to avoid silent data loss.

Recommended parsing pattern (non-code guidance):
- Read `properties(neighbor)` and `labels(neighbor)` exactly like now.
- For the edge, use `properties(r)` (already returned) and add `source_id`/`target_id` from `parent_id` and `neighbor_id` in the query result.
- Do not use `record.data()` or `Result.graph()` because they drop labels/edge properties or lose structural information.
- Consume the result fully before issuing the next query (driver requirement).

### 2.3. Output formats

Each `RetrievalResult` should have exporter helpers:

1) **React/D3.js output**
    - Method: `to_d3()`
    - Output: `{"nodes": [...], "links": [...]}` with unique nodes and edges.
    - Deduplicate nodes by `id` and edges by `(source_id, target_id, type)`.
    - Include the following fields:
      - Nodes: `id`, `labels`, `properties`, `activation` (if needed), `score` (seed score if applicable).
      - Links: `source`, `target`, `type`, `weight`, `tags`, `transfer_energy`, `properties`.
    - Include a consistent node ID for the seed even if it appears in multiple paths.

2) **LLM context string**
    - Method: `to_llm_context()`
    - Output: a list of path strings plus a compact JSON summary.
    - Format example:
      - `Path 1: [Seed N3000] (UserRequest: "...") -> [RELATES w=0.82 T=0.103] -> (DataSource: "...") ...`
    - Include only key properties: `id`, main text, title, or short description. Exclude embeddings and raw vectors.
    - Provide transfer energy and edge weight in the string so LLM can assess strength.
    - Also include a machine-readable block (same as `to_d3()`), appended for LLMs to dive into attributes if needed.

3) **Manual debug Cypher**
        - Method: `to_debug_cypher()`
        - Output: a ready-to-run Cypher query string that reconstructs the exact path in Neo4j Desktop.
        - Pattern (single path):
            - Use the ordered node ids from a path and construct a strict path match:
                - `MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1})-[:RELATES]-(n2 {id: $id2}) RETURN p`
        - Pattern (multiple paths):
            - Provide one query per path
        - How to read ids:
            - For each `GraphPath`, read `steps` in order and collect: `steps[0].from_node.id`, then each `steps[i].to_node.id`.
            - This produces the full ordered node id list used to build the Cypher path pattern.

### 2.4. Performance notes

- Parsing should be done in a single pass over records returned from Neo4j.
- Deduplication should be done with dict/set lookups on IDs.
- Avoid deep copies; use shallow copies of `properties` when needed.
- Output methods should not re-run queries; they should only format already stored data.

## 3. Test Strategy Plan

**Goal:** Build a layered test suite that verifies mathematical correctness, Cypher behavior, BFS logic, and overall reasonableness using the dummy dataset in src/tests/memorygraph.

### 3.1. Test framework and setup

- Use `pytest` + `pytest-asyncio`.
- Add a `conftest.py` with:
    - `event_loop` fixture (pytest-asyncio standard).
    - `neo4j_driver` fixture using `AsyncGraphDatabase.driver` that is created once per test session and reused.
    - ensure session uses `database="testmemory"`.
- Tests should assume the dummy data is already loaded in the database. Do not reload or reset data during tests.
- Avoid concurrency in tests: no parallel AsyncSessions in the same test.
- Tests should be small and deterministic.

### 3.2. Phase 1: Unit tests for pure Python logic

Target: traversal state behavior _without the database_!

1) **Frontier selection and deduplication**
    - Arrange: build a fake frontier and a candidates_by_parent map with known transfer energies.
    - Act: call `select_next_frontier()` with `max_branches=2`.
    - Assert:
      - Only top 2 candidates selected per parent.
      - If two parents try to claim the same neighbor, only the highest energy wins.
      - Newly visited set contains the selected neighbors.

2) **Completed path logic**
    - Arrange: frontier nodes with paths, and zero candidates for a parent.
    - Act: call the update method.
    - Assert: frontier node is moved to `completed_paths` only if it has a non-empty path.

3) **Max depth completion**
    - Arrange: frontier nodes with existing paths at the end of loop.
    - Act: call `finalize_remaining()`.
    - Assert: all remaining paths are added.

#### Expanded Phase 1: Unit Tests for Pure Python Logic (Including Parsers)

Target: test traversal state, path construction, and output formatting without touching Neo4j.

A. Traversal state tests (no DB):

1) **Frontier selection and deduplication**
    - Initialize: `seed_node = GraphNode(id="S", labels=["Seed"], properties={})` and `traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)`.
    - Build `frontier: list[FrontierNode]` with `FrontierNode(node_id, activation, path)` where `path` uses `GraphPath.empty()` or previously extended paths.
    - Create `candidates_by_parent` mapping with `ExpansionCandidate` objects whose `neighbor_node.id` intentionally collides across parents to validate that the highest `transfer_energy` wins the claim.
    - Assert: only top-2 per parent chosen, winners are chosen by energy, and `newly_visited` contains the selected neighbor ids.

2) **Completed path logic**
    - Setup a frontier node with a non-empty `path` and zero candidates in `candidates_by_parent`.
    - Call `select_next_frontier()` and assert the path is returned in `completed_paths`.

3) **Max depth completion**
    - Provide a remaining `frontier` with extended `GraphPath` objects and call `finalize_remaining()`.
    - Assert all non-empty paths are returned.

B. Parser output tests (no DB):

1) **`to_d3()` minimal sanity**
    - Minimal input: one seed node and one 1-hop path.
    - create a minimal input called `result` and assert the parsing logic correctly produces nodes and links with expected fields.

2) **`to_llm_context()` minimal sanity**
    - Using the same `result` above, call `to_llm_context(result)`.
    - Assertions:
      - The returned dict has a `paths` list with a string starting with `"Path 1: [Seed S1]"` and containing `"RELATES"` and `T=0.120` (approx formatting check).
      - The returned `graph` equals `to_d3(result)`.

3) **`to_debug_cypher()` minimal sanity**
    - Using the same `result`, call `to_debug_cypher(result)`.
    - Assertion: returns a list containing the exact Cypher pattern
      `MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p` (string equality) and that parameter placeholders correspond to the node ordering used in the path.

Notes for parser tests:
- Keep inputs minimal and deterministic.
- Use string comparisons for formatting checks, but prefer partial string assertions when whitespace/rounding may vary (e.g., `assert "RELATES" in s and "T=0.120" in s`).

### 3.3. Phase 2: Cypher + math validation tests (integration)

Target: validate the transfer energy and tag similarity computations.

1) **Transfer energy math check**
    - Test multiple edges across different parts of the dummy graph.
    - For each test case:
      - Choose a seed node from dummy_data_cypher.txt and assign a seed score R (e.g., 0.85).
      - Choose query tags (test input) to control tag overlap with edge tags from dummy data.
      - Extract edge weight and tags from dummy_data_cypher.txt.
      - Calculate parent degree D by counting RELATES edges in dummy data (or query the graph).
      - Compute expected T manually: $T = (R * w / \sqrt{d}) * tag\_sim$.
      - Run `expand_frontier` with the chosen seed and query tags, then match the candidate for the edge under test.
      - Assert returned `transfer_energy` equals expected using `pytest.approx`.
      - Include at least one case with a missing edge weight to confirm the default weight is applied.

2) **Tag similarity floor check**
    - Run expansion with empty query tags.
    - Assert that `tag_sim` used is exactly `1.0` (no tag filtering).
    - Run expansion with tags that do not overlap any edge tags.
    - Assert the transfer energy uses the `tag_sim_floor`.
    - Run a partial overlap case and a full overlap case to confirm the floor + Jaccard scaling.
    - Use at least two different edges with different tag sets to confirm behavior is consistent.

3) **Degree penalty check**
    - Identify multiple parent nodes with different degrees (at least three distinct degrees).
    - For each, choose edges with equal weights and comparable tag overlap.
    - Expect the higher degree parent to pass less energy (all else equal).
    - Document the degree counts directly from the dummy data and verify them manually.

4) **Minimum activation filter check**
    - Identify at least one candidate edge whose computed transfer energy is below `min_activation`.
    - Run `expand_frontier` and confirm the candidate is excluded from results.

5) **Data correctness guardrails**
    - Before asserting values, document each tested node and edge in the test docstring with the exact properties from dummy_data_cypher.txt.
    - The developer must read the dummy data carefully and confirm all expected values to avoid false failures.

#### Expanded Phase 3: BFS Logic + End-to-End Tests

- Building `GraphRetriever` in tests:
  - For DB-backed tests use `GraphRetriever(neo4j_driver, GraphRetrieverConfig(database="testmemory", max_depth=..., min_activation=..., max_branches=...))`.
  - For unit tests, inject a fake connector into a `GraphRetriever` instance: `retriever._connector = FakeConnector(...)` then call `_explore_single()` by creating a fake session or monkeypatching `self._driver.session` to return a fake session whose `execute_read(fn)` calls `fn(fake_tx)`.

- Collecting results from `explore()`:
  - `results = [r async for r in retriever.explore([seed], query_tags)]` and assert on `results[0].paths`, `max_depth_reached`, and `terminated_reason`.

- Add explicit tests for `seed_not_found`:
  - Create a fake connector that returns `SeedFetchResult(node=None, labels=[], found=False)` and assert returned `RetrievalResult.terminated_reason == "seed_not_found"`.

### 3.4. Phase 3: BFS logic + end-to-end tests

Target: end-to-end path formation is correct and results are reasonable.

1) **Single depth expansion**
    - Choose a seed node from dummy data with 3+ neighbors (e.g., T3000 has several).
    - Set query tags to match some edges (e.g., ['campaign']).
    - Run full exploration with `max_branches=2`.
    - Assert exactly 2 neighbors are expanded, ordered by descending transfer energy.
    - Verify the paths are 1-hop long.

2) **Multi-depth traversal**
    - Choose a seed node with at least 2 depth levels (e.g., T3000 can reach T3003 via T3002).
    - Set query tags to allow traversal (e.g., ['campaign']).
    - Run full exploration.
    - Assert paths end when below threshold or at max depth.
    - Validate that `max_depth_reached` equals the longest path length (e.g., 2 or 3).

3) **Cycle avoidance**
    - Identify if dummy data has cycles (e.g., check for bidirectional edges or loops).
    - If present, run exploration and assert no node ID repeats within any path.
    - If no cycles, skip or note that cycle avoidance is implicit.

### 3.5. Phase 4: Reasonableness tests (human-expected relevance)

Target: ensure the algorithm retrieves plausible memory paths given the dummy data.

1) **Expected path retrieval**
    - Define 2-3 scenarios: seed node + query tags with obvious topical matches.
    - Read dummy_data_cypher.txt to document why edges are favored (high weight, tag overlap etc).
    - Run exploration and assert the returned paths include those expected sequences. leave some flexibility tho, we are testing reasonableness, not exact matches. There are some completely unreasonable paths that should be excluded for any seed and user query. We want to make sure those are excluded while seeing if the reasonable ones are included.

2) **Unexpected path rejection**
    - Identify edges that are weakly connected or off-topic (e.g., low weight like 0.35 from T3003 to T4001).
    - Run with default thresholds and assert these paths are absent.

3) **Threshold sensitivity**
    - Pick a scenario where a path is absent at default `min_activation` (e.g., 0.005).
    - Lower the threshold (e.g., to 0.002) and rerun.
    - Assert the new path appears only with the lower threshold.

### 3.6. Test documentation requirements

- Every test must include a docstring that states:
  - Scenario
  - Expected output
  - Why it should hold (math or dummy data reasoning)
- Add inline comments only for non-obvious constants or calculations.
- make sure you carefully read graph_retriever.py, models.py, retriever_parser.py, and dummy_data_cypher.txt to avoid misreading the data. It's pivotal that the "ecpected" values in tests are correct based on the dummy data that exists. It's also pivotal that tests call the correct functions and initialize them correctly.

### 3.7. Additional Implementation Details and Parser Tests

- Best practices / gotchas:
  - Tests must avoid creating multiple concurrent `AsyncSession` objects in the same test function; share a single `neo4j_session` or use sequential `async with` blocks.
  - For unit tests that should not touch the DB, patch or inject a fake `Neo4jConnector` into `GraphRetriever` (e.g., `retriever._connector = FakeConnector(...)`) or call `GraphTraversalState` directly.
  - The `GraphRetriever.explore()` API returns an async iterator; collect results with `results = [r async for r in retriever.explore([seed], query_tags)]` or `async for r in retriever.explore(...): ...`.
  - To avoid waiting during retry tests, set `GraphRetrieverConfig(max_retries=0)`.
  - Use `pytest.approx` for floating-point comparisons.

