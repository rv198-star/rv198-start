# GRAPH_REPORT

## Snapshot
- source_snapshot: `poor-charlies-almanack-v0.1`
- graph_version: `kiu.graph/v0.2`
- nodes: `15`
- edges: `10`
- communities: `5`

## God Nodes
1. **Circle of competence** (`n_circle_principle`) | type=`skill_principle` | degree=`4`
2. **Margin of safety sizing** (`n_margin_principle`) | type=`skill_principle` | degree=`3`
3. **Bias self audit** (`n_bias_principle`) | type=`skill_principle` | degree=`2`
4. **Invert the problem** (`n_invert_principle`) | type=`skill_principle` | degree=`2`
5. **Anti-ruin checklist** (`n_inversion_checklist_trace`) | type=`usage_trace` | degree=`1`

## Communities
### Boundary discipline
- top_node: **Circle of competence** (`n_circle_principle`)
- node_count: `4`
- modularity_score: `0.1667`
- nodes: Bias self audit, Circle of competence, Career offer OOD case, Surface familiarity trap
### Error avoidance
- top_node: **Bias self audit** (`n_bias_principle`)
- node_count: `4`
- modularity_score: `0.3333`
- nodes: Bias self audit, US Air regret, Anti-ruin checklist, Invert the problem
### Risk control
- top_node: **Margin of safety sizing** (`n_margin_principle`)
- node_count: `3`
- modularity_score: `0.6667`
- nodes: Margin of safety sizing, See's Candies discipline, Salomon exposure cap
### Capital allocation
- top_node: **Costco next best benchmark** (`n_costco_switch_trace`)
- node_count: `3`
- modularity_score: `0.3333`
- nodes: Costco next best benchmark, Google omission, Opportunity cost of the next best idea
### Reference evaluations
- top_node: **Career offer OOD case** (`n_eval_ood_career_offer`)
- node_count: `2`
- modularity_score: `0.0`
- nodes: Career offer OOD case, Surface familiarity trap

## Surprising Connections
- No cross-community inferred or ambiguous connections yet.

## Suggested Questions
1. Why does `Circle of competence` sit at the center of this graph, and what evidence would most change its routing?
2. Why does `Margin of safety sizing` sit at the center of this graph, and what evidence would most change its routing?
3. What is the operational boundary of `Boundary discipline`, and should it stay agentic or downgrade to workflow?
4. What is the operational boundary of `Error avoidance`, and should it stay agentic or downgrade to workflow?
5. Which missing evidence would most improve confidence for `Boundary discipline`?
