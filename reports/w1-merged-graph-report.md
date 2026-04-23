# GRAPH_REPORT

## Snapshot
- source_snapshot: `<unknown>`
- graph_version: `kiu.graph.merge/v0.2`
- nodes: `24`
- edges: `25`
- communities: `8`
- bundle_count: `2`
- source_bundles: `engineering-postmortem-v0.1`, `poor-charlies-almanack-v0.1`

## God Nodes
1. **Blast radius check** (`engineering-postmortem-v0.1::n_blast_radius_principle`) | type=`skill_principle` | degree=`8`
2. **Bias self audit** (`poor-charlies-almanack-v0.1::n_bias_principle`) | type=`skill_principle` | degree=`5`
3. **Blameless postmortem** (`engineering-postmortem-v0.1::n_postmortem_principle`) | type=`skill_principle` | degree=`5`
4. **Circle of competence** (`poor-charlies-almanack-v0.1::n_circle_principle`) | type=`skill_principle` | degree=`5`
5. **Margin of safety sizing** (`poor-charlies-almanack-v0.1::n_margin_principle`) | type=`skill_principle` | degree=`5`

## Communities
### Learning loop
- top_node: **Blameless postmortem** (`engineering-postmortem-v0.1::n_postmortem_principle`)
- node_count: `4`
- modularity_score: `0.5`
- nodes: DB index rollback blame, Blameless postmortem, Runbook ownership reset, Timeline gap incident
### Pre-change and postmortem shared frame
- top_node: **Blast radius check** (`engineering-postmortem-v0.1::n_blast_radius_principle`)
- node_count: `3`
- modularity_score: `0.6667`
- nodes: Blast radius check, Blameless postmortem, Reversibility gate
### Release safety
- top_node: **Blast radius check** (`engineering-postmortem-v0.1::n_blast_radius_principle`)
- node_count: `5`
- modularity_score: `0.4`
- nodes: Blast radius check, Feature flag guard, Irreversible migration precheck, Phased rollout holdback, Reversibility gate
### Boundary discipline
- top_node: **Bias self audit** (`poor-charlies-almanack-v0.1::n_bias_principle`)
- node_count: `4`
- modularity_score: `0.1667`
- nodes: Bias self audit, Circle of competence, Career offer OOD case, Surface familiarity trap
### Capital allocation
- top_node: **Costco next best benchmark** (`poor-charlies-almanack-v0.1::n_costco_switch_trace`)
- node_count: `3`
- modularity_score: `0.3333`
- nodes: Costco next best benchmark, Google omission, Opportunity cost of the next best idea
### Error avoidance
- top_node: **Bias self audit** (`poor-charlies-almanack-v0.1::n_bias_principle`)
- node_count: `4`
- modularity_score: `0.3333`
- nodes: Bias self audit, US Air regret, Anti-ruin checklist, Invert the problem
### Reference evaluations
- top_node: **Career offer OOD case** (`poor-charlies-almanack-v0.1::n_eval_ood_career_offer`)
- node_count: `2`
- modularity_score: `0.0`
- nodes: Career offer OOD case, Surface familiarity trap
### Risk control
- top_node: **Margin of safety sizing** (`poor-charlies-almanack-v0.1::n_margin_principle`)
- node_count: `3`
- modularity_score: `0.6667`
- nodes: Margin of safety sizing, See's Candies discipline, Salomon exposure cap

## Surprising Connections
- **Bias self audit** -> **Blast radius check** | type=`complements` | kind=`INFERRED` | confidence=`0.66` | cross_bundle=`true` | concepts=`boundary_control, learning_audit` | support_refs=`4`
- **Reversibility gate** -> **Bias self audit** | type=`complements` | kind=`INFERRED` | confidence=`0.63` | cross_bundle=`true` | concepts=`error_avoidance, learning_audit` | support_refs=`3`
- **Bias self audit** -> **Blameless postmortem** | type=`complements` | kind=`AMBIGUOUS` | confidence=`0.56` | cross_bundle=`true` | concepts=`learning_audit` | support_refs=`4`

## Suggested Questions
1. Why does `Blast radius check` sit at the center of this graph, and what evidence would most change its routing?
2. Why does `Bias self audit` sit at the center of this graph, and what evidence would most change its routing?
3. What is the operational boundary of `Learning loop`, and should it stay agentic or downgrade to workflow?
4. What is the operational boundary of `Pre-change and postmortem shared frame`, and should it stay agentic or downgrade to workflow?
5. Which missing evidence would most improve confidence for `Learning loop`?
