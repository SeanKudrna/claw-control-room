# Issue #43 Research — Game-Style Skill Tree UI

Date: 2026-02-18

## Visual reference patterns (game UIs)

1. **Path of Exile Passive Skill Tree**  
   https://www.pathofexile.com/passive-skill-tree  
   - Massive connected node web with clear progression paths.
   - Uses visual link lines to communicate unlock dependencies.
   - Node prominence + icon hierarchy communicates major/minor passives.

2. **World of Warcraft Talent Calculator (modern class/spec trees)**  
   https://www.wowhead.com/talent-calc  
   - Branching progression with explicit parent-child dependency lines.
   - Tiered depth and strong active/locked state signaling.
   - Selection focus combines map context + detail panel.

3. **General skill-tree pattern framing**  
   https://en.wikipedia.org/wiki/Skill_tree  
   - Core UX traits: branching choices, dependency gating, and visible progression depth.

## React-compatible implementation options evaluated

### Option A — `@xyflow/react` (React Flow)
- Refs: https://reactflow.dev/ and https://reactflow.dev/examples
- Pros:
  - Strong node/edge primitives out of the box.
  - Interaction model (zoom/pan/selection/custom nodes) already built.
  - Mature OSS ecosystem and docs.
- Cons (for this issue scope):
  - Adds dependency weight and interaction surface we do not currently need.
  - Requires adapting state shape and map constraints for simple deterministic tier rendering.

### Option B — `react-d3-tree`
- Ref: https://github.com/bkrem/react-d3-tree
- Pros:
  - Built for hierarchical tree rendering with links.
  - Good defaults for classic rooted trees.
- Cons:
  - Our data can express multi-dependency DAG-like relationships (not strict single-parent tree).
  - Styling to game-like cards + deterministic lane control would still require significant overrides.

### Option C — `@projectstorm/react-diagrams`
- Ref: https://github.com/projectstorm/react-diagrams
- Pros:
  - Extensible and supports complex graph editors.
- Cons:
  - Heavier framework than needed for a read-only progression map.
  - Better fit for editable process diagrams than compact dashboard skill visualization.

### Option D — Custom lightweight SVG connectors + CSS grid (chosen)
- Pros:
  - Zero new dependencies; keeps bundle and maintenance minimal.
  - Full control over “game-like” look (connectors, glow, tiers, states).
  - Easy deterministic tier layout and mobile fallback strategy.
- Cons:
  - We own layout logic and connector rendering.

## Decision

**Choose Option D (custom implementation)** for issue #43.

Rationale:
- Fastest path to a true game-style visual tree in the current codebase.
- Delivers clear branch connectors, tier hierarchy, and state distinction without introducing heavy graph runtime.
- Maintains compatibility with existing `skills.nodes` payload and detail panel behavior.
