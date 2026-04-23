from __future__ import annotations

import re
from typing import Any


def build_semantic_contract(
    *,
    candidate_id: str,
    title: str | None = None,
    primary_snippet: str | None = None,
) -> dict[str, Any]:
    del title
    del primary_snippet

    semantic_family = identify_semantic_family(candidate_id)
    family_contract = _build_family_contract(semantic_family)
    if family_contract is not None:
        return family_contract

    symbol_root = candidate_id.replace("-", "_")
    return {
        "trigger": {
            "patterns": [
                f"{symbol_root}_decision_required",
                f"{symbol_root}_evidence_grounded",
            ],
            "exclusions": [
                "concept_query_only",
                f"{symbol_root}_outside_operating_boundary",
            ],
        },
        "intake": {
            "required": [
                {
                    "name": "scenario",
                    "type": "structured",
                    "description": "Scenario summary that may require this principle or skill.",
                },
                {
                    "name": "decision_goal",
                    "type": "string",
                    "description": "The concrete decision, tradeoff, or next action under review.",
                },
                {
                    "name": "decision_scope",
                    "type": "string",
                    "description": "What part of the decision is in scope, and what must stay outside the boundary.",
                },
                {
                    "name": "current_constraints",
                    "type": "list[string]",
                    "description": "Operational constraints, missing context, or boundary conditions that could block firing.",
                },
                {
                    "name": "disconfirming_evidence",
                    "type": "list[string]",
                    "description": "Evidence that would make this skill unsafe to apply or require deferral.",
                },
            ]
        },
        "judgment_schema": {
            "output": {
                "type": "structured",
                "schema": {
                    "verdict": "enum[apply|defer|do_not_apply]",
                    "next_action": "string",
                    "evidence_to_check": "list[string]",
                    "decline_reason": "string",
                    "confidence": "enum[low|medium|high]",
                },
            },
            "reasoning_chain_required": True,
        },
        "boundary": {
            "fails_when": [
                "disconfirming_evidence_present",
                f"{symbol_root}_evidence_conflict",
            ],
            "do_not_fire_when": [
                "scenario_missing_decision_context",
                f"{symbol_root}_boundary_unclear",
            ],
        },
    }


def identify_semantic_family(candidate_id: str) -> str:
    normalized = str(candidate_id or "")
    normalized = re.sub(r"-source-note$", "", normalized)
    return normalized


def _build_family_contract(semantic_family: str) -> dict[str, Any] | None:
    if semantic_family == "circle-of-competence":
        return {
            "trigger": {
                "patterns": [
                    "user_entering_unfamiliar_domain",
                    "user_claiming_should_be_able_to_figure_it_out",
                ],
                "exclusions": [
                    "concept_query_only",
                    "experienced_operator_already_inside_circle",
                    "objective_comparison_request",
                ],
            },
            "intake": {
                "required": [
                    {
                        "name": "target",
                        "type": "entity",
                        "description": "Asset, company, role, or domain currently under consideration.",
                    },
                    {
                        "name": "user_background",
                        "type": "structured",
                        "description": "Demonstrated exposure, operating history, and actual decision record in the domain.",
                    },
                    {
                        "name": "decision_goal",
                        "type": "string",
                        "description": "The concrete decision or commitment the user wants to make now.",
                    },
                    {
                        "name": "capital_at_risk",
                        "type": "number",
                        "description": "How much capital, reputation, or career downside is truly at stake.",
                    },
                    {
                        "name": "disconfirming_evidence",
                        "type": "list[string]",
                        "description": "Evidence showing the user cannot yet explain the business, failure path, or key falsifiers.",
                    },
                ]
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "verdict": "enum[in_circle|edge_of_circle|outside_circle]",
                        "missing_knowledge": "list[string]",
                        "recommended_action": "enum[proceed|study_more|decline]",
                        "evidence_to_check": "list[string]",
                        "decline_reason": "string",
                        "confidence": "enum[low|medium|high]",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": [
                    "product_familiarity_overstated_as_understanding",
                    "user_background_too_vague_to_test_depth",
                ],
                "do_not_fire_when": [
                    "concept_query_only",
                    "experienced_operator_already_inside_circle",
                    "objective_comparison_request",
                ],
            },
        }
    if semantic_family == "invert-the-problem":
        return {
            "trigger": {
                "patterns": [
                    "user_asking_how_plan_can_fail",
                    "user_worried_plan_is_too_optimistic",
                    "team_only_sees_opportunity_not_threat",
                    "user_requesting_systematic_red_team_review",
                ],
                "exclusions": [
                    "concept_query_only",
                    "pure_brainstorming_only",
                    "outcome_already_decided",
                    "option_comparison_without_failure_scan",
                ],
            },
            "intake": {
                "required": [
                    {
                        "name": "objective",
                        "type": "string",
                        "description": "The concrete outcome the user wants to achieve.",
                    },
                    {
                        "name": "constraints",
                        "type": "list[string]",
                        "description": "Deadlines, irreversibilities, and known operating constraints.",
                    },
                    {
                        "name": "ruin_conditions",
                        "type": "list[string]",
                        "description": "What would make the plan fail in a way that is costly or hard to recover from.",
                    },
                    {
                        "name": "disconfirming_evidence",
                        "type": "list[string]",
                        "description": "Evidence showing the objective or failure map is still too vague to optimize safely.",
                    },
                ]
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "failure_modes": "list[string]",
                        "avoid_rules": "list[string]",
                        "first_preventive_action": "string",
                        "edge_posture": "enum[full_inversion|partial_review|defer]",
                        "evidence_to_check": "list[string]",
                        "decline_reason": "string",
                        "confidence": "enum[low|medium|high]",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": [
                    "objective_still_too_vague_for_inversion",
                    "inversion_used_as_post_hoc_decoration",
                    "low_stakes_plan_overengineered_without_material_gain",
                ],
                "do_not_fire_when": [
                    "concept_query_only",
                    "pure_brainstorming_only",
                    "outcome_already_decided",
                    "option_comparison_without_failure_scan",
                ],
            },
        }
    if semantic_family == "bias-self-audit":
        return {
            "trigger": {
                "patterns": [
                    "user_showing_high_conviction_under_commitment_pressure",
                    "user_resisting_counterevidence_or_group_dissent",
                    "group_consensus_before_commitment",
                    "supporting_evidence_only_collected",
                ],
                "exclusions": [
                    "concept_query_only",
                    "early_research_only",
                    "urgent_incident_response",
                    "historical_explanation_only",
                    "data_collection_request_only",
                ],
            },
            "intake": {
                "required": [
                    {
                        "name": "thesis",
                        "type": "string",
                        "description": "The current view or decision thesis in the user's own words.",
                    },
                    {
                        "name": "incentives",
                        "type": "list[string]",
                        "description": "Incentives, identity exposure, or social pressure that could distort judgment.",
                    },
                    {
                        "name": "reversibility",
                        "type": "string",
                        "description": "How costly it is to reverse the decision if the thesis is wrong.",
                    },
                    {
                        "name": "disconfirming_evidence",
                        "type": "list[string]",
                        "description": "Best counter-evidence the user should examine before committing further.",
                    },
                    {
                        "name": "commitment_window",
                        "type": "string",
                        "description": "Whether the user is about to approve, publish, buy, or otherwise lock in the decision soon.",
                    },
                ]
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "triggered_biases": "list[string]",
                        "severity": "enum[low|medium|high]",
                        "mitigation_actions": "list[string]",
                        "next_action": "string",
                        "audit_mode": "enum[full_audit|partial_review|defer]",
                        "evidence_to_check": "list[string]",
                        "decline_reason": "string",
                        "confidence": "enum[low|medium|high]",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": [
                    "no_live_commitment_to_audit",
                    "request_is_really_domain_analysis_not_bias_audit",
                    "historical_or_data_collection_request_without_live_thesis",
                ],
                "do_not_fire_when": [
                    "concept_query_only",
                    "early_research_only",
                    "urgent_incident_response",
                    "historical_explanation_only",
                    "data_collection_request_only",
                ],
            },
        }
    if semantic_family == "value-assessment":
        return {
            "trigger": {
                "patterns": [
                    "user_asking_if_price_is_detached_from_value",
                    "user_comparing_quality_against_current_valuation",
                    "user_testing_if_market_panic_created_mispricing",
                    "user_considering_private_business_or_angel_valuation",
                ],
                "exclusions": [
                    "concept_query_only",
                    "short_term_trading_request",
                    "pure_scale_comparison_request",
                    "business_quality_comparison_without_live_price_decision",
                ],
            },
            "intake": {
                "required": [
                    {
                        "name": "value_anchor",
                        "type": "structured",
                        "description": "Intrinsic-value anchor, cash-generation logic, or business economics that justify calling the asset valuable at all.",
                    },
                    {
                        "name": "quality_drivers",
                        "type": "list[string]",
                        "description": "Moat, pricing power, management quality, reinvestment runway, and other business-quality drivers that sustain value.",
                    },
                    {
                        "name": "price_or_valuation",
                        "type": "string",
                        "description": "The current market price, entry multiple, private valuation, or check-level terms under review.",
                    },
                    {
                        "name": "market_or_liquidity_context",
                        "type": "structured",
                        "description": "Why the asset may be mispriced now, including panic, illiquidity, refinancing pressure, or private-market frictions.",
                    },
                    {
                        "name": "disconfirming_evidence",
                        "type": "list[string]",
                        "description": "Evidence showing the claimed value anchor is weak, circular, speculative, or detached from the real business.",
                    },
                ]
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "valuation_posture": "enum[undervalued|fairly_priced|overvalued|no_value_anchor]",
                        "applicability_mode": "enum[full_valuation|partial_applicability|refuse]",
                        "key_value_drivers": "list[string]",
                        "boundary_warnings": "list[string]",
                        "next_action": "string",
                        "handoff": "enum[delegate_to_sizing|monitor_only|decline]",
                        "evidence_to_check": "list[string]",
                        "decline_reason": "string",
                        "confidence": "enum[low|medium|high]",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": [
                    "value_anchor_missing_or_circular",
                    "price_story_detached_from_business_economics",
                    "speculation_presented_as_intrinsic_value",
                ],
                "do_not_fire_when": [
                    "concept_query_only",
                    "short_term_trading_request",
                    "pure_scale_comparison_request",
                    "pure_scale_or_competition_comparison_without_value_question",
                ],
            },
        }
    if semantic_family == "margin-of-safety-sizing":
        return {
            "trigger": {
                "patterns": [
                    "user_asking_if_price_is_reasonable_under_uncertainty",
                    "user_deciding_position_size_or_capital_commitment",
                    "user_testing_price_vs_quality_tradeoff",
                    "user_asking_if_panic_creates_mispricing",
                    "user_considering_private_business_or_angel_check",
                ],
                "exclusions": [
                    "concept_query_only",
                    "short_term_trading_request",
                    "pure_scale_comparison_request",
                    "business_quality_comparison_without_live_price_decision",
                ],
            },
            "intake": {
                "required": [
                    {
                        "name": "downside_range",
                        "type": "structured",
                        "description": "Estimated downside range, ruin conditions, and what happens if the thesis is early or wrong.",
                    },
                    {
                        "name": "liquidity_profile",
                        "type": "structured",
                        "description": "Liquidity, exit friction, refinancing dependence, and fallback capital.",
                    },
                    {
                        "name": "conviction_basis",
                        "type": "string",
                        "description": "Why the user believes an edge exists beyond a generic upside story.",
                    },
                    {
                        "name": "disconfirming_evidence",
                        "type": "list[string]",
                        "description": "Evidence showing the current thesis lacks enough downside, liquidity, or boundary math.",
                    },
                    {
                        "name": "entry_price_or_check_size",
                        "type": "string",
                        "description": "The actual price, valuation range, or capital check under consideration right now.",
                    },
                ]
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "sizing_band": "enum[tiny|small|medium|concentrated|refuse]",
                        "constraints": "list[string]",
                        "rationale": "string",
                        "next_action": "string",
                        "applicability_mode": "enum[full_sizing|partial_applicability|refuse]",
                        "evidence_to_check": "list[string]",
                        "decline_reason": "string",
                        "confidence": "enum[low|medium|high]",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": [
                    "downside_or_liquidity_math_missing",
                    "upside_story_used_as_permission_to_size",
                    "quality_story_without_price_or_check_decision",
                ],
                "do_not_fire_when": [
                    "concept_query_only",
                    "short_term_trading_request",
                    "pure_scale_comparison_request",
                    "business_quality_comparison_without_live_price_decision",
                ],
            },
        }
    return None
