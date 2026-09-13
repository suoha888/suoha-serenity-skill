# Advanced bottleneck diagnostics v4

Use this guide for Standard and Deep research, or whenever a theme appears to
depend on a scarce component, material, process, qualification, or permit. It
turns a plausible story into an auditable chain. It is a research procedure,
not an investment recommendation.

## 1. Start with architecture necessity

Before counting suppliers, write the system requirement that the proposed node
must satisfy. Then describe at least one credible alternative architecture.
Compare the alternatives on:

- performance, reliability, energy, latency, density, or safety;
- redesign and requalification work;
- deployment delay and customer switching cost;
- availability of substitute inputs and equipment;
- regulatory, geographic, or standards constraints.

Use `supported` only when a dated source establishes why the node is required.
If a customer can bypass it without a material penalty, mark the bottleneck
`not_established` even if the supplier is popular or concentrated.

## 2. Record the supply-chain edge

Do not write “Company X is exposed to the theme” as if it were a relationship.
For each material edge, record:

```text
upstream entity
  -> product or process
  -> relationship type
  -> downstream entity or system dependency
  -> effective period
  -> evidence and counterevidence
  -> alternative supplier and alternative architecture
```

Relationship types include `supplies`, `design_in`, `qualifies`,
`reserves_capacity`, `contracts_with`, `depends_on`, `alternative_to`, and
`integrates`. A product page can establish that a product exists; it normally
cannot establish a named customer, qualified status, market share, pricing
power, or economic capture by itself.

## 3. Use capacity states, not one capacity number

Keep these states separate. A later state cannot be inferred from an earlier
state without evidence:

| State | Meaning | Typical proof |
|---|---|---|
| nominal | nameplate or theoretical output | technical specification or announcement |
| installed | equipment or line physically installed | capex/project milestone |
| usable | output after uptime, yield, labor, and input constraints | operating data |
| qualified | output accepted for a particular customer/specification | qualification or design-in evidence |
| merchant | output available to external customers | allocation, order, or segment disclosure |
| captive | output reserved for internal use or an affiliated customer | internal allocation or business-model evidence |
| available | uncommitted output after reservations and priority claims | dated backlog/capacity disclosure |

For every state, store value, unit, `as_of`, epistemic type, evidence IDs, and
unknowns. A large nominal expansion with no qualified or merchant output is a
capacity hypothesis, not supply proof.

## 4. Test the thirteen dimensions independently

The first eight describe the familiar bottleneck and value-capture questions;
the last five close common gaps:

1. `supplier_concentration` — how many credible suppliers meet the required spec?
2. `substitutability` — can the customer switch without redesign or requalification?
3. `qualification_burden` — how long, costly, and customer-specific is approval?
4. `expansion_lead_time` — how quickly can qualified supply be added?
5. `customer_urgency` — what operational cost follows a late delivery?
6. `capacity_visibility` — can orders, backlog, utilization, and ramp be observed?
7. `pricing_power` — can the supplier retain economics rather than only volume?
8. `economic_value_capture` — does this company capture the scarce value?
9. `architecture_necessity` — is the node required by the chosen architecture?
10. `yield_manufacturability` — can the process repeat at the required yield and quality?
11. `merchant_vs_captive_capacity` — is supply actually available to the market?
12. `geographic_regulatory_concentration` — do jurisdiction, permits, export controls, or standards matter?
13. `capital_intensity` — what capex, working capital, and funding are needed to scale?

Do not average these dimensions. A high bottleneck rating cannot repair an
unresolved architecture gate, weak customer evidence, or absent value capture.

## 5. Walk the validation ladder in order

Use one status and one evidence set for each rung:

```text
architecture necessity
  -> physical supply
  -> customer validation
  -> company capture
  -> financial transmission
  -> market expectations
```

The first five rungs answer whether a real operating opportunity exists. The
last rung asks whether the market proxy appears to price a different future.
Do not use a high multiple, price move, or prominent investor narrative to
upgrade an unresolved operating rung.

## 6. Separate strategic importance from company capture

For each candidate, resolve the following independently:

```text
chain edge
  -> qualified product or capacity
  -> customer use and repeat volume
  -> unit volume / ASP / mix
  -> segment revenue
  -> margin and working capital
  -> capex / debt / equity financing
  -> dilution and per-share economics
```

“The system needs it” is not “this ticker earns the rent.” A company with only
thematic adjacency is `thematic_only`; a relevant segment with no evidence of
pricing or margin capture remains `plausible` or `not_established`.

## 7. Run the reflexivity audit

When a social post, influential author, newsletter, or community discussion is
part of the lead, record:

- whether the thesis originated socially;
- whether the source could influence the market;
- whether the post preceded the price move;
- whether independent fundamental evidence arrived afterward;
- whether the price action is independent evidence.

If the post precedes the move and independent fundamental confirmation is not
`yes`, price action must remain non-independent or unknown. Engagement,
follower count, reposts, and post-performance are not evidence of supply,
qualification, customer urgency, or economic capture.

## 8. Required failure tests

Every deep output should search for at least one item in each category:

- architecture bypass or product redesign;
- qualified second source or rapid competitor expansion;
- customer dual-sourcing, vertical integration, or bargaining power;
- capacity that is nominal, captive, reserved, or unusable rather than merchant;
- volume growth without ASP, margin, cash conversion, or per-share improvement;
- capex or financing that absorbs the operating benefit;
- social reflexivity or hindsight contamination.

For every unresolved item, state the exact source or metric that would resolve
it and the time window for the check. If the check cannot be specified, leave
the proposition `UNKNOWN` rather than inventing confidence.

## 9. Method-card quality bar

When distilling historical public material into a method card, preserve the
transferable rule and its boundary, not a personality or ticker list. Each card
should expose:

```text
works_when
fails_when
known counterexample
alternative explanations
required evidence
disconfirming evidence
```

Later price performance can be stored only in evaluator-only outcomes. It must
not rewrite the method card or upgrade the evidence state of an earlier claim.
