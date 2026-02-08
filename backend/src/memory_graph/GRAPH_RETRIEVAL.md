# Retrieval Graph Algorithm

## 1. Purpose & Context

Memory retrieval in Project Memoria follows a **two-stage design**:

1. **Vector Search** *(already complete by the time GraphRetriever is called)*:
   Semantic similarity search identifies a handful of **seed nodes** (up to 5) whose text closely matches the user query. Each seed comes with a **hybrid similarity score** $R(Mi)$ that blends vector search and BM25 search. These seeds are the starting points for graph exploration.

2. **Graph Exploration** *(this module)*:
   Starting from each seed, we traverse the Neo4j knowledge graph outward to discover **connected memories** that provide rich contextual evidence for an AI agent to answer the user's query.

This document describes our **Activation Energy Algorithm**: a graph traversal method inspired by associative memory retrieval in the human brain. The algorithm models "mental energy" spreading outward from a triggered memory (the seed), progressively activating related memories along weighted, topically relevant connections. Only paths with sufficient accumulated energy are retained, filtering noise automatically and producing high-confidence contextual paths.


## 2. Notation
Understand the notation below used to describe the algorithm.

| Symbol | Type | Meaning |
|--------|------|---------|
| $M_i$ , $M_j$ | Node | Memory nodes in our Neo4j knowledge graph. |
| $R(M_i)$ | float ∈ (0, 1] | **Hybrid similarity score** of seed node Mi, produced by the upstream vector search. For non-seed nodes during traversal, R becomes the Transfer Energy received from the previous hop. |
| $w_{ij}$ | float ∈ [0.25, 1.0] | **Edge weight** between Mi and Mj (stored as `weight` property on the edge). Higher = stronger relationship. |
| $d(M_i)$ | int ≥ 1 | **Degree** of node Mi: total count of connected edges in all directions. |
| $T(M_i→M_j)$ | float | **Transfer Energy**: the computed activation passed from Mi to Mj along their connecting edge. |
| `Q` | string | The user's query text. |
| `Qtags` | list[str] | Tag keywords extracted from the user query. |
| `eTags` | list[str] | Tags stored on a specific edge (`tags` property). |
| `MAX_DEPTH` | int (default 5) | Maximum number of hops from the seed node in any single path. |
| `MIN_ACTIVATION` | float (default 0.005) | Minimum Transfer Energy to continue exploring a branch. |
| `TAG_SIM_FLOOR` | float (default 0.15) | Baseline tag similarity for the blending function. |
| `MAX_BRANCHES` | int (default 3) | Maximum number of neighbors to expand per node at each depth level. |


## 3. Tag Overlap Similarity

Both edges and queries carry tag lists. Edges are assigned tags at the time of creation. Queries are given tags at the time of retrieval. We need a function to measure how **topically aligned** an edge is with the current query. We use a **floored Jaccard coefficient**:

```python
tag_sim(eTags, Qtags):

    if |Qtags| = 0:
        return 1.0                  # no query tags → no tag-based filtering

    if |eTags| = 0:
        return TAG_SIM_FLOOR        # untagged edge → small baseline

    jaccard = |eTags ∩ Qtags| / |eTags ∪ Qtags|

    return TAG_SIM_FLOOR + (1.0 − TAG_SIM_FLOOR) × jaccard
```

### Why Floored Jaccard?

- **Pure Jaccard** returns 0 when tags don't overlap. This would completely block traversal even on structurally important edges.
- The **floor** (default 0.15) guarantees that any edge can still be traversed if the weight and activation energy are high enough.
- Tag overlap provides up to a **~7× boost** over the floor, strongly preferring topically aligned paths without being binary.

### Why Jaccard?

- **Fast**: O(n) with set intersection/union.
- **Bounded** [0, 1]: directly compatible with the Transfer Energy product.
- **Symmetric**: $\text{sim}(A, B) = \text{sim}(B, A)$.
- **Works with short lists**: typical tags are 3–8 items; Jaccard handles this naturally.

### Worked Example

```
Edge tags:  ["inventory_policy", "recommendation", "analysis_dependency"]
Query tags: ["demand_forecasting", "stockout", "safety_stock", "inventory_policy"]

Intersection: {"inventory_policy"} → |intersection| = 1
Union:        6 items                → |union| = 6
Jaccard:      1/6 ≈ 0.167

tag_sim = 0.15 + 0.85 × 0.167 = 0.292
```

Compare to an edge with no tag overlap with the query:
```
tag_sim = 0.15 + 0.85 × 0.0 = 0.15   (still traversable, but penalized)
```

## 4. Transfer Energy Function

The core equation governing energy propagation from node $M_i$ to neighbor $M_j$ through their connecting edge:

$$T(M_i \to M_j) = \frac{ R(M_i) \times w_{ij} }{ \sqrt{d(M_i)} } \times \text{tag\_sim}(\text{eTags}_{ij}, \text{Qtags})$$

### Why √d instead of d?

We normalize by degree to penalize hub nodes. But raw degree (`d`) is too harsh it causes energy to drop off so quickly that paths rarely exceed depth 2. By using the square root of degree (`√d`), we soften this penalty so that paths can regularly reach depth 3–5 while still discouraging hubs.

### Propagation Rule

After selecting neighbor Mj, we set:

$$R(Mj) \leftarrow T(Mi \to Mj)$$

The transfer energy **becomes** Mj's activation for the next traversal step. This is the recursive core of the algorithm. Each node's activation is determined entirely by the energy it received.


## 5. Multi-Path Exploration

### The Problem with Single-Path (Greedy Top-1)

If we only follow the single best neighbor at each hop, we produce one linear path per seed. But a seed node often connects to multiple valuable directions e.g., a `UserRequest` might link to several `DataSource` nodes and an `AgentAction`, each leading to different contextual memories. A single path misses most of this context.

### Design: Breadth-First Multi-Branch Expansion

From each seed, we explore **all promising directions simultaneously** using a level-by-level BFS. At each depth level, every active frontier node expands its top `MAX_BRANCHES` neighbors (above threshold). Each branch proceeds independently and terminates when its energy decays below `MIN_ACTIVATION` or it hits `MAX_DEPTH`.

```
Depth 0 (seed):       [N2006]
                      /   |   \
Depth 1:          [N2003] [N2004] [N2005]     ← top-3 neighbors by T
                    |       |       ✗ (T < threshold → branch ends)
Depth 2:          [N2001] [N2008]
                    |       ✗ (T < threshold)
Depth 3:          [N2010]
                    ✗ (T < threshold)

Resulting paths:
  Path A: seed → N2003 → N2001 → N2010  (depth 3)
  Path B: seed → N2004 → N2008           (depth 2)
  Path C: seed → N2005                    (depth 1)
```

### Algorithm Step-by-Step

```
1.  INITIALIZE
    ├─  Fetch seed node from Neo4j
    ├─  frontier  ← [ { node_id: seed_id, activation: R(seed), path: [] } ]
    ├─  visited   ← { seed_id }
    └─  completed_paths ← []

2.  LOOP for depth = 0 to MAX_DEPTH-1:
    │
    ├─  If frontier is empty → BREAK (all branches terminated)
    │
    ├─  2a. BATCHED EXPANSION (single Cypher round-trip):
    │       Send ALL frontier nodes at once via UNWIND.
    │       For each frontier node, compute T for all unvisited neighbors.
    │       Return all above-threshold candidates, sorted by T desc per parent.
    │
    ├─  2b. GROUP & SELECT:
    │       For each frontier node, take top MAX_BRANCHES neighbors.
    │       Skip neighbors already claimed by another frontier node this level
    │       (highest T wins ties).
    │
    ├─  2c. UPDATE:
    │       Frontier nodes with zero surviving candidates → their path is COMPLETE.
    │       Append completed paths to results.
    │       New frontier ← all selected neighbors with their paths extended.
    │       Add all new frontier node IDs to visited.
    │
    └─  2d. Continue loop.

3.  FINALIZE
    ├─  Any remaining frontier nodes at MAX_DEPTH → their paths are COMPLETE.
    └─  Return all completed paths for this seed.
```

## 6. Cypher Queries

The cypher queries used in the algorithm are detailed below.

### 6.1 Seed Fetch

```cypher
MATCH (n {id: $node_id})
RETURN properties(n) AS data, labels(n) AS labels
```

### 6.2 Batched Frontier Expansion

All frontier nodes are expanded in a **single Cypher query** per depth level. Transfer Energy is computed entirely in Cypher. Python only receives above-threshold candidates.

```cypher
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
```

**Design notes:**
- **`UNWIND $frontier`** — one row per frontier node. All frontier nodes expand in a single DB call.
- **`sqrt(toFloat(degree))`** — the softened degree normalization.
- **No `LIMIT`** — returns all above-threshold candidates. Python handles per-parent top-K since `MAX_BRANCHES` is Python-side config and result set is small.
- **`ORDER BY parent_id, transfer_energy DESC`** — groups candidates by parent with highest T first, so Python can slice the first K per group.
- **Bidirectional match** `(current)-[r:RELATES]-(neighbor)` — traverses edges in both directions since seeds can be any node type.


## 7. Termination Conditions

| Condition | Trigger | Outcome |
|-----------|---------|---------|
| **Max depth** | Any branch reaches `MAX_DEPTH` hops | That branch's path is complete. Other branches may terminate earlier. |
| **Below threshold** | No neighbor exceeds `MIN_ACTIVATION` | That branch is complete at its current depth. |
| **Dead end** | All neighbors already in `visited` set | Cycle avoided. Branch is complete. |
| **Empty frontier** | All branches terminated before `MAX_DEPTH` | Exploration finishes early. |
| **Seed not found** | `seed_id` doesn't exist in graph | Return empty result with `"seed_not_found"`. |


## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Multi-path BFS, not single-path greedy** | Seeds often connect to multiple valuable directions. BFS captures all of them with the same number of Cypher round-trips (one per depth level). |
| **`MAX_BRANCHES = 3` per node** | Limits worst-case frontier growth to $3^5 = 243$, but in practice energy decay + threshold keep it to ~5–15 total paths. |
| **`√d` degree normalization** | Raw `d` kills energy too fast — paths rarely exceeded depth 2. `√d` lets paths regularly reach depth 3–5 while still penalizing hubs. |
| **`MIN_ACTIVATION = 0.005`** | Low enough to reach depth 4–5 on well-connected topical paths. High enough to filter genuinely irrelevant branches. |
| **`TAG_SIM_FLOOR = 0.15`** | A non-zero floor prevents hard blocks on structurally important edges. 0.15 gives enough baseline that a high-weight causal edge can still propagate even without tag overlap. |
| **One `AsyncSession` per exploration** | Sessions are not concurrency-safe. Each task gets its own session from the driver's pool. |
| **`execute_read()` for transactions** | Automatic retry on transient errors, read routing in clustered setups, clean transaction lifecycle. Exploration is naturally idempotent (pure reads). |
| **Driver connection pool (shared)** | The `AsyncDriver` manages its own pool. Shared across all concurrent explorations. Created once at app startup. |
| **Exponential backoff on retry** | $0.05s \times 2^{\text{attempt}}$. Brief delay prevents hammering a recovering server. |
| **`asyncio.as_completed` (not gather)** | `gather` waits for ALL tasks. `as_completed` yields results as each finishes — critical for downstream streaming. |


## 9. Recommended Indexes

Without indexes, `MATCH (n {id: $current_id})` performs a full node scan. For graphs beyond ~1,000 nodes, create property indexes per label:

```cypher
CREATE INDEX idx_userrequest_id    IF NOT EXISTS FOR (n:UserRequest)    ON (n.id);
CREATE INDEX idx_usepreference_id  IF NOT EXISTS FOR (n:UserPreference) ON (n.id);
CREATE INDEX idx_agentanswer_id    IF NOT EXISTS FOR (n:AgentAnswer)    ON (n.id);
CREATE INDEX idx_agentaction_id    IF NOT EXISTS FOR (n:AgentAction)    ON (n.id);
CREATE INDEX idx_event_id          IF NOT EXISTS FOR (n:Event)          ON (n.id);
CREATE INDEX idx_datasource_id     IF NOT EXISTS FOR (n:DataSource)     ON (n.id);
```
.
