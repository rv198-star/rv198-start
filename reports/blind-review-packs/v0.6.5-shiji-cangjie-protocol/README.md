# Blind Review Pack: v065-shiji-cangjie-protocol-blind

Files for external reviewers:

- `reviewer-pack.json`: anonymous A/B cases.
- `reviewer-response-template.json`: fill `preferred`, dimension scores, and notes.

Private file for maintainers only:

- `private-unblind-key.json`: maps A/B options to hidden origins. Do not send this to reviewers.

After review, merge the response with the private key to create `blind-preference-review-v0.1` evidence.
