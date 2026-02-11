## Parser Output Changes

### `to_debug_cypher()` - BREAKING CHANGE

#### Old Output Format
Returns a `list[str]` of individual Cypher queries with parameterized IDs:
```python
[
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p",
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p",
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1})-[:RELATES]-(n2 {id: $id2}) RETURN p",
]
```

#### New Output Format
Returns a `dict[str, Any]` with **literal embedded IDs** and both individual + combined queries:
```python
{
  "paths_combined": "MATCH p0 = (n0_0 {id: \"N3204\"})-[:RELATES]-(n0_1 {id: \"N5001\"}), p1 = (n1_0 {id: \"N3204\"})-[:RELATES]-(n1_1 {id: \"N5002\"}) RETURN p0, p1",
  "individual_paths": [
    "MATCH p0 = (n0_0 {id: \"N3204\"})-[:RELATES]-(n0_1 {id: \"N5001\"}) RETURN p0",
    "MATCH p1 = (n1_0 {id: \"N3204\"})-[:RELATES]-(n1_1 {id: \"N5002\"}) RETURN p1",
  ]
}
```

#### Key Changes
1. **Literal IDs**: IDs are now embedded directly in the query strings (no `$id0` parameters). This makes queries executable without parameter binding.
2. **Return type**: Changed from `list[str]` to `dict[str, Any]`.
3. **Two query variants**:
   - `individual_paths`: List of standalone Cypher queries, one per branch (for debugging single paths)
   - `paths_combined`: A single multi-MATCH statement showing all branches connected to the same seed node (for visualizing the algorithm's full exploration)
4. **Node aliases**: Each path gets unique node aliases (`n{path_idx}_{node_idx}`) to avoid collisions when running the combined query.
5. **ID escaping**: Literal strings are properly escaped (backslash and quote handling) to ensure valid Cypher syntax.

#### Test Migration Guide
- Any tests expecting `list[str]` must be updated to expect `dict[str, Any]`.
- Update assertions to check `result["individual_paths"]` for single-path queries.
- Update assertions to check `result["paths_combined"]` for multi-path graph visualization.
- Tests should verify that IDs are literal strings (e.g., `"N3204"`) rather than parameterized (`$id0`).