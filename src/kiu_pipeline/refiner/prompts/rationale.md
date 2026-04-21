You are drafting the `Rationale` section for a KiU skill.

Return only the section body as plain Markdown. Do not include headings, YAML fences, or commentary.

Constraints:
- Keep the text grounded in the supplied anchors and trace references.
- Meet the minimum density target: at least {{min_chars}} characters and at least {{min_anchor_refs}} anchor-style references.
- Use KiU anchor reference format such as `[^anchor:<anchor-id>]` and `[^trace:<trace-path>]`.
- Explain the judgment logic, when it should fire, and what failure mode it is protecting against.
- Stay aligned with the existing Contract; do not invent new trigger symbols or relation targets.

Skill:
- skill_id: {{skill_id}}
- title: {{title}}
- round: {{round_index}}

Current Rationale:
{{current_rationale}}

Evidence Summary:
{{evidence_summary}}

Usage Summary:
{{usage_summary}}

Available Source Anchors:
{{source_anchor_list}}

Available Graph Anchors:
{{graph_anchor_list}}

Available Trace References:
{{trace_ref_list}}

Produce a denser replacement `Rationale` section now.
