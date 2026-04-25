# Condition-Dependent Validation Backlog

This document tracks validation sources that KiU should use when the required external conditions exist. These items do not block short-term foundation releases unless a version explicitly promotes them into release gates.

## External Blind Review

- Current status: unavailable as a reliable multi-reviewer process.
- Trigger condition: at least three reviewers or independent model/human panels can evaluate masked artifacts with balanced A/B assignment and no attribution leakage.
- Future gate use: may become an external preference closure score for same-source or same-book comparisons.
- Current claim boundary: internal usage and proxy scores must not be described as external blind preference.

## Real User Validation

- Current status: no stable user task pool.
- Trigger condition: recurring user tasks can be collected with source, prompt, artifact, outcome, and user judgment traces.
- Future gate use: may become real usage quality evidence for practical usefulness.
- Current claim boundary: generated usage and proxy prompts are internal regression evidence only.

## Live-Web Factual Validation

- Current status: explicitly out of scope for v0.7.0/v0.7.1 no-web foundation releases.
- Trigger condition: a source category needs current facts before safe application, such as investment, financial planning, regulation, medical, legal, or current market decisions.
- Future gate use: may become a before-use freshness check with source citation requirements.
- Current claim boundary: no-web world alignment may ask for current context or refuse; it must not assert current facts.

## Domain-Expert Validation

- Current status: unavailable.
- Trigger condition: a qualified reviewer can judge field-specific usefulness, misuse risk, and factual caveats for a domain bundle.
- Future gate use: may become a domain release gate for high-risk or high-cost domains.
- Current claim boundary: internal value metrics are not domain-expert validation.
