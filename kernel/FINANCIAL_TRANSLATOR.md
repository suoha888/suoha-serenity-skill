# Financial Translator

Use this module after the bottleneck and evidence work. It translates an
operating claim into shareholder economics; it does not create evidence for an
unverified claim.

## Fixed bridge

```text
industry event
  -> volume / ASP / utilization
  -> revenue
  -> gross profit
  -> operating profit
  -> cash flow
  -> funding requirement
  -> dilution
  -> per-share economics
```

For every input, label it as reported, externally verified, inferred, assumed,
or unknown. Preserve the source and `as_of` date beside the input.

## Required checks

- Separate industry growth, company revenue growth, and per-share value.
- Check revenue mix, gross margin, operating leverage, working capital, capex,
  debt, cash runway, financing method, and new-share risk.
- Distinguish management targets from signed orders, customer qualification,
  production, and recognized revenue.
- Show a range when inputs are estimates; do not produce false precision.
- If a required input is missing, output `UNKNOWN` and state the resolving check.

## Minimum report fields

```text
Operating driver:
Input / source / as_of / confidence:
Revenue bridge:
Gross-profit bridge:
Cash requirement:
Funding path:
Dilution or per-share impact:
Key sensitivity:
What would invalidate the bridge:
```

Keep valuation optional and downstream of evidence. A good industry, a good
company, and a good stock are separate conclusions.
