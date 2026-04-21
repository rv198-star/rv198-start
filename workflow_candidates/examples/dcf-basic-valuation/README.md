# dcf-basic-valuation

This example shows the v0.3 workflow script artifact shape for a `workflow_script_candidate`.

It is intentionally schema-only:

- no execution engine is implied
- no branching or loops are used
- the file is designed for validator and reviewer consumption first

The example encodes a minimal discounted cash flow workflow:

1. discount projected free cash flows
2. discount terminal value
3. add both present values into a single output
