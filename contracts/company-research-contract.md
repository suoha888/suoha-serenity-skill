# Company Research Contract v4

This contract governs the conversion of a supply-chain bottleneck into a
dated, auditable company research object.

## 1. Identity before interpretation

Resolve `legal_name + ticker + exchange + market + quote_currency` together.
If two listed entities match a ticker, stop at `UNKNOWN` and request an
unambiguous identifier or use an authoritative exchange/filing source. Do not
silently select the most popular company.

## 2. Company basics are first-class facts

The CompanyProfile must cover, or explicitly mark UNKNOWN:

- main business and business model;
- reporting segments and revenue mix with period, unit, currency, and source;
- named or unnamed customer exposure and concentration;
- geographies and policy/FX exposure;
- competitors and substitution set;
- revenue, margins, operating cash flow, free cash flow, capex, debt/cash,
  working capital, financing, and dilution indicators;
- main operating, accounting, governance, geopolitical, liquidity, and design
  risks.

The profile must also separate three judgments:

- `exposure_assessment`: what exact product or process links the company to the
  chain, how the relationship is established, and whether it is direct,
  qualified, design-in, contracted, inferred, or merely thematic;
- `capture_assessment`: how the company could retain value, whether the relevant
  segment is material, and whether pricing power is observed or only plausible;
- `capital_structure`: funding status, share-count basis, liquidity, and
  dilution risk as of a dated source.

“AI exposure”, “core supplier”, “large customer”, and “leader” are claims, not
fields that may be inferred from a product page or social post alone.

## 3. MarketSnapshot rules

Record the quote and capitalization separately:

```text
price = value + quote_currency + price_type + price_as_of + source
market_cap = value + currency + market_cap_basis + market_cap_as_of + source
shares = value + shares_basis + shares_as_of + source
```

Allowed market-cap bases are `reported`, `price_times_basic_shares`,
`price_times_diluted_shares`, and `unknown`. A weighted-average income-statement
share count is not automatically the current shares outstanding. If the price
and shares dates do not align, state the mismatch and downgrade freshness.

Currency conversion requires a dated FX evidence item and must preserve the
original quote. Do not compare market caps across markets as if currencies,
share classes, or trading sessions were interchangeable.

## 4. Bottleneck-to-value-capture bridge

The company is relevant only if the chain position can plausibly capture the
constraint. Test, in order:

```text
physical constraint
  -> qualification / capacity / utilization / yield
  -> unit volume or ASP / mix / repeat rate
  -> segment revenue
  -> margin and working capital
  -> capex / debt / financing / dilution
  -> per-share economics (if the inputs support it)
```

A strong bottleneck with weak company exposure is not a strong company thesis.
A high-growth company with no evidence of bottleneck value capture remains a
lead. Mark the bridge UNKNOWN where an input cannot be verified.

The bottleneck object now assesses thirteen dimensions independently:

```text
supplier concentration
substitutability
qualification burden
expansion lead time
customer urgency
capacity visibility
pricing power
economic value capture
architecture necessity
yield / manufacturability
merchant versus captive capacity
geographic / regulatory concentration
capital intensity
```

It also records a supply-chain edge and the separate capacity states nominal,
installed, usable, qualified, merchant, captive, and available. A nameplate
number or expansion announcement does not establish qualified merchant supply.

## 5. Variant perception and conditional reasons

The report must distinguish:

- a market proxy: price, multiple, consensus estimate, disclosed guidance, or
  another dated expectation signal;
- the hypothesis about what the market may be underestimating;
- the causal mechanism connecting the bottleneck to economics;
- the evidence supporting and contradicting the hypothesis;
- the metric and time window that would confirm or falsify the hypothesis.

Use this form for each research reason:

```text
IF [condition]
THEN [implication for supply chain and company economics]
BECAUSE [evidence-backed mechanism]
CONFIRM WITH [metric/source and time window]
FAIL IF [specific counterevidence]
```

This is a research-priority statement, not a buy/sell recommendation. Avoid
`buy`, `sell`, `hold`, `guaranteed`, `certain`, target price, and expected
return language in the structured conclusion.

Before the expectation gap, walk the six-stage validation ladder in order:

```text
architecture necessity
  -> physical supply
  -> customer validation
  -> company capture
  -> financial transmission
  -> market expectations
```

Also render a reflexivity audit whenever a social post or influential public
source is part of the lead. If the post precedes the price move and independent
fundamental confirmation is absent, the price move is not independent evidence.

## 6. Source routing

Prefer exchange filings, regulators, company IR, audited reports, transcripts,
standards, customer/supplier filings, project documents, patents, and credible
trade sources according to the market. Social posts are leads. A source that
cannot be opened, dated, or tied to the claim is `UNVERIFIED` or `UNKNOWN`.

Every material field keeps its own evidence IDs. A single citation at the end
of a paragraph is not enough when the paragraph contains price, market cap,
customer, margin, and competitor facts.
