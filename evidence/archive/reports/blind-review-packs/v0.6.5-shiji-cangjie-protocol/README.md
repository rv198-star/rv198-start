# Blind Review Pack: v065-shiji-cangjie-protocol-blind

Files for external reviewers:

- `reviewer-pack.json`: anonymous A/B cases.
- `reviewer-response-template.json`: fill `preferred`, dimension scores, and notes.

Private file for maintainers only:

- `private-unblind-key.json`: maps A/B options to hidden origins. Do not send this to reviewers.

After review, merge the response with the private key to create `blind-preference-review-v0.1` evidence.

## Superseded

This v0.6.5 review pack is retained for audit history only. It is superseded by `reports/blind-review-packs/v0.6.6-shiji-cangjie-protocol/` because the original pack could emit one placeholder side when generated KiU skills lived under `bundle/skills/<skill_id>/SKILL.md`. Do not use this pack as external blind evidence.
