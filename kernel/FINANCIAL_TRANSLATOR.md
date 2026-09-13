# Financial Translator v4

Use this module after the bottleneck and evidence work. It translates an
operating claim into shareholder economics; it does not create evidence for an
unverified claim. It is a bridge, not a valuation oracle.

## Fixed bridge

```text
industry event
  -> qualified merchant volume / ASP / utilization
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

## Business-model branches

Select the closest branch before building the bridge. Do not reuse a
manufacturing formula for a royalty or project business:

- **Capacity manufacturer:** qualified merchant capacity × utilization × ASP,
  then yield, mix, gross margin, working capital, and capex. Keep nominal,
  installed, usable, qualified, merchant, captive, and available capacity
  separate.
- **Equipment supplier:** systems shipped × ASP + service/consumables, then
  backlog conversion, installation timing, service margin, and customer capex.
- **Consumable/material supplier:** qualified units × consumption per unit ×
  price, then repeat rate, qualification, mix, and inventory effects.
- **IP/royalty supplier:** licensed units × royalty rate, then adoption timing,
  contract scope, collection, and concentration.
- **Project/infrastructure supplier:** awarded backlog × execution rate, then
  milestone billing, completion risk, working capital, and financing.
- **Diversified company:** build each material segment separately before
  consolidating; never infer company-wide exposure from one product mention.

## Required checks

- Separate industry growth, company revenue growth, and per-share value.
- Check revenue mix, gross margin, operating leverage, working capital, capex,
  debt, cash runway, financing method, and new-share risk.
- Distinguish management targets from signed orders, customer qualification,
  production, and recognized revenue.
- Separate company exposure from company capture. A system bottleneck does not
  establish that the candidate owns the edge or retains the rent.
- Record whether capex creates merchant qualified supply or only captive,
  reserved, or nominal capacity.
- Treat a quoted price and market cap as separate dated facts. Record quote
  type, exchange, currency, source, shares basis, market-cap basis, and
  freshness. Do not translate currencies without a dated FX source.
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

## Research-case boundary

Valuation context should answer what the current price appears to imply and
what the market may be underestimating, not manufacture a target price or
expected return. Express “why it may be worth further research” as:

```text
IF [condition is confirmed by a dated metric/source]
THEN [the bottleneck can plausibly reach this company economics path]
BECAUSE [evidence-backed mechanism]
FAIL IF [specific falsification metric or counterevidence]
```

Keep valuation optional and downstream of evidence. A good industry, a good
company, and a good stock are separate conclusions. A research priority is
not a buy/sell instruction.
