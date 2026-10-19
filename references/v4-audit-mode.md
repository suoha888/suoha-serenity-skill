# v4 audit mode (full integrity procedure)

Load this file when the user asks for the full audit / deep research bundle,
for structured company research artifacts (ResearchOutput, research bundle),
or for historical method distillation. The default Serenity lens fast path in
SKILL.md already enforces the core rules; this file holds the complete v4
procedure that previously lived in SKILL.md (moved verbatim in v6.1.0).

## Non-negotiable integrity rules

1. Set an explicit research_cutoff before retrieving evidence.
2. Filter historical cases on known_at or published_at, never import time.
3. Keep epistemic_type separate from evidence_state:
   FACT, INFERENCE, HYPOTHESIS, UNKNOWN versus SUPPORTED, STALE,
   CONTRADICTED, NOT_ESTABLISHED.
4. Every material claim needs evidence IDs, source locator, timestamps,
   provenance, and a confidence level.
5. Treat social posts as leads. Verify material company claims with primary
   filings, exchange documents, company IR, transcripts, regulators, standards,
   project documents, patents, or credible trade sources.
6. Test supplier concentration, qualification, expansion time, substitution,
   customer validation, capacity visibility, and economic capture before ranking
   a company.
7. Search for contradictory evidence and an alternative explanation
   deliberately.
8. If a source is missing, stale, inaccessible, or ambiguous, say UNKNOWN,
   STALE, or NOT_ESTABLISHED and state the exact resolving check.
9. Later prices, returns, engagement, or outcomes never upgrade a historical
   claim or method card.
10. Never invent a source, customer, order, price, contract, market cap,
    financial input, tool result, or personal fact.
11. Treat the physical bottleneck as a first-class object. Record supplier
    concentration, substitutability, qualification burden, expansion lead
    time, customer urgency, capacity visibility, pricing power, and economic
    value capture separately; never collapse them into one score.
12. A company-level answer must expose a dated CompanyProfile and MarketSnapshot
    (ticker, exchange, currency, price, market-cap basis, shares, business,
    mix, customers, geography, competitors, financial quality, and risks).
    Missing or stale market facts are UNKNOWN or STALE, never filled from
    memory.
13. “What the market may be missing” is a testable variant-perception
    hypothesis. “Why consider buying” may only be expressed as conditional
    research reasons with proof metrics, time windows, and failure conditions;
    it is never a trade instruction, target-price promise, or return forecast.
14. Use separate dimensions for bottleneck strength, evidence, economic
    capture, valuation context, catalyst timing, and risk. A single composite 0–100
    conviction score is prohibited because it creates false precision.
15. Treat `architecture_necessity` as the first gate. If the system can bypass
    the proposed node without a material redesign, qualification, or performance
    loss, the bottleneck is not established. An unresolved architecture gate is
    an explicit UNKNOWN, never an implied positive.
16. Separate nominal, installed, usable, qualified, merchant, captive, and
    available capacity. Never promote a capacity announcement, nameplate number,
    or management target into qualified supply without dated evidence.
17. Record the supply-chain edge itself: upstream entity, product/process,
    downstream dependency, relationship type, effective period, evidence,
    counterevidence, and alternative supplier or architecture. A product mention
    or thematic adjacency is not a verified edge.
18. A company-level output must separate direct chain exposure from economic
    capture and from capital structure. The `CompanyProfile` must expose an
    exposure assessment, capture assessment, and dated funding/dilution view.
19. Walk the validation ladder in order: architecture necessity, physical
    supply, customer validation, company capture, financial transmission, and
    market expectations. Do not use a later rung to compensate for an unresolved
    earlier rung.
20. Run a reflexivity audit when social or author-originated material is present.
    A price move after a post is non-independent market evidence until separately
    confirmed by fundamentals; engagement is never evidence of a bottleneck.
21. For ticker research, follow the decision-first layout in
    contracts/output-contract.md: a compact verdict card, then five scannable
    sections. State the bottleneck verdict, company position/capture, and equity
    research priority separately. Quick mode may shorten explanations, but may
    not omit any of the thirteen dimensions, six validation stages, evidence
    status, counterevidence, or unknowns. Keep the method and timeline audit
    visible in the evidence appendix, even when no approved match or event is
    available. Do not create a long sequence of peer-level headings or repeat
    the same fact in multiple sections.
22. Use explicit status labels defined in the output contract. `PARTIAL` means
    at least one material link is evidenced but another required link is open;
    `NOT_ESTABLISHED` means evidence is insufficient, not that the claim is
    false; `CONTRADICTED` requires direct contrary evidence. Separate the
    existence of a bottleneck, the company's chain position, economic capture,
    and valuation context. Do not hide a missing link behind words such as
    “possibly,” “likely,” or “may”; name the missing proof and the check that
    would resolve it.
23. Select only applicable `human_reviewed` method cards before broad current-
    evidence retrieval. Convert each selected card into a ticker-specific
    verification question; the card itself is never evidence for the answer.
    If no approved card is available, say so and use the canonical framework—
    never silently substitute a candidate, pending, or rejected card.
24. Retrieve ticker-specific historical thesis events only after synthesizing
    current evidence. Present a short dated timeline with event IDs and before /
    after states; do not quote or reproduce archive posts, use popularity or
    returns as proof, or let historical stance override current counterevidence.

Read the canonical contracts in contracts/output-contract.md,
contracts/provenance-contract.md, contracts/temporal-contract.md, and
contracts/access-control-contract.md, and
contracts/company-research-contract.md when the request produces a structured
company research artifact.

## Request routing

- Theme scan: map the system and layers first, then rank scarce layers and
  company research priorities. Produce the validation ladder before ranking.
- Serenity-style ticker or theme question (default): follow the v6 eight
  steps (live snapshot, atlas, lead scan, primary documents, fit/status/phase,
  valuation, variant perception, gated delivery); attach the v4 audit bundle
  when the user asks for depth.
- "Is this a Serenity stock?": answer framework_fit first. A weak or
  not_applicable fit is a valid, useful answer; do not force a chokepoint.
- Single-company challenge: resolve the entity and chain position, render a
  CompanyProfile and MarketSnapshot, verify the supply-chain edge,
  customer/capacity/economics, reflexivity, and state the strongest downgrade
  condition.
- Candidate comparison: keep bottleneck strength, evidence, proximity, finance,
  valuation context, catalyst timing, and risk as separate dimensions; never
  rank by a single additive score.
- Company research: resolve the issuer and cutoff; select applicable approved
  method cards and turn them into verification questions; collect current
  company and market evidence independently; complete the thirteen dimensions,
  six-stage ladder, and financial bridge; then render the decision-first report
  and compare relevant dated thesis events in the evidence appendix.
- Thesis update: represent the change as a dated thesis event with before,
  after, trigger evidence, and remaining unknowns.
- Research partner or learning mode: ask one focused question at a time and
  move from story to system change to scarce layer to proof.
- Historical distillation: use only the local normalized JSONL pipeline and
  produce reviewable candidate artifacts; never upload the archive or call a
  remote model with local material.

## Standard research procedure

1. Define the question, market, intended decision, time window, and explicit
   research cutoff.
2. Resolve the ticker to the legal issuer, exchange, market, and quote currency.
   Establish only enough current business context to select relevant method
   cards; label unresolved identity or business facts instead of guessing.
3. For ticker/company research, load only applicable local method cards with
   `review_status: human_reviewed`. Record their IDs and translate their
   transferable rules into concrete questions for this issuer. If none qualify,
   record that no approved card was applied and continue with the canonical
   framework. Never search raw archives or use candidate/pending/rejected cards
   as research authority.
4. Map the system change, value-chain layers, candidate edges, alternatives,
   and architecture necessity. Use the method-derived questions to guide what
   to verify—not to predetermine the result.
5. Retrieve current evidence independently from method cards and historical
   thesis events. Resolve each question with dated, claim-level sources; a card
   or social post can be a lead, not proof of a current company fact.
6. Create the BottleneckAssessment: test architecture necessity first, assess
   all thirteen dimensions independently, and classify all capacity states.
7. Build the CompanyProfile and MarketSnapshot. Separate direct exposure,
   economic capture, and funding/dilution; keep reported and calculated market
   values distinct and dated.
    If an official quote page fails, use the bounded fallback in
    references/market-source-playbook.md before declaring market data missing.
    A provider quote does not validate its share count or capitalization.
8. Build the Claim Ledger, grade evidence quality/freshness/independence, and
   verify material claims. Complete the six-stage validation ladder in order.
9. Translate the operating mechanism through the business-model-specific
   volume/ASP/utilization-to-revenue, profit, cash, funding, dilution, and
   per-share bridge—or mark unsupported links UNKNOWN.
10. Search deliberately for contradictory evidence and alternative
    explanations; run the reflexivity audit where social material is present.
11. Only after the current-evidence synthesis, retrieve relevant company-specific
    thesis events available by the cutoff. Render up to six material events in
    date order, with event IDs and before/after states, then compare them with
    current evidence. Historical events explain how the thesis changed; they do
    not establish current truth.
12. State market-implied expectations, variant-perception hypotheses,
    conditional research reasons, catalysts, and invalidation conditions.
13. Render the decision-first layout in contracts/output-contract.md. Quick
    mode shortens explanations, not required evidence fields. Keep the verdict
    card up front; check that bottleneck existence, issuer position/capture, and
    stock-level research priority are not conflated. Include all thirteen
    separately named dimensions, seven capacity states, six validation rungs,
    method-card mapping, thesis-history status, dated market snapshot,
    counterevidence, unknowns, and provenance. Remove repeated facts and
    unexplained hedging. If a required item is missing, finish it or mark the
    report PARTIAL; never present an outline as a complete research result.
14. For structured research, run `scripts/validate_research_bundle.py` on the
    complete local object bundle described in references/research-bundle.md.
    A successful `validate_research_output.py` run checks structure only, not
    source existence or truth. If no Python tool is available, disclose that
    automated validation was not run; manually check the same links. Do not
    require an OpenAI API key: the host agent performs research with its
    available tools, while the bundled scripts remain local and network-free.

Use `scripts/method_catalog.py --data-root <local-data-root> --partition public
--as-of <cutoff> --approved-only` to discover usable local methods. Query by
mechanism (qualification, capacity, capture), not ticker alone. Subscription
methods require an explicitly private workflow and never enter public output.
No approved match is a valid fallback, not evidence that the historical corpus
has been reviewed. Never create a human approval on a user's behalf.

The shared reasoning and mode budgets are in kernel/RESEARCH_KERNEL.md. Quick,
Standard, and Deep modes change evidence budget and response depth, never the
integrity rules.

## Historical method distillation

Read references/distillation-playbook.md for the complete local workflow.
The deterministic implementation is scripts/distill_archive.py. It consumes
normalized records only:

~~~text
normalized records
  -> context packs
  -> entities and relations
  -> claims and lead evidence
  -> thesis-event candidates
  -> candidate method cards
  -> human review queue
~~~

Public and subscription partitions are physically separate. Every derived
object inherits its input access level. Candidate method cards are not
authoritative until independently reviewed. Keep temporal holdouts sealed and
keep outcomes in an evaluator-only layer.

## Local architecture

- kernel/: stable reasoning procedure, financial translation, thesis lifecycle,
  and validation gates.
- schemas/: machine-readable object contracts.
- contracts/: output, provenance, time, and access invariants.
- adapters/: normalized source boundary; adapters acquire data but do not infer
  investment conclusions.
- references/: conditional detailed playbooks, including advanced bottleneck
  diagnostics and output routing.
- evals/: synthetic fixtures and deterministic integrity checks.
- scripts/: local validators, distillation, index, build, and verification.
- assets/ and examples/: reusable templates and public-safe examples.

JSONL is the canonical data format. SQLite + FTS5 is an optional local index
with mandatory partition and time filters. Do not add vector databases, graph
databases, full OCR, or a Web UI unless an evaluation proves the simpler
structured path insufficient.

The only editable copy is the source repository. scripts/build_runtime.py
generates the runtime; scripts/verify_runtime.py rejects drift and unmanaged
files. The runtime contains no raw archive or private overlay.

serenity-content-skill and an infographic compiler are downstream consumers.
They may format a ResearchOutput but may not alter facts, thesis state, source
provenance, access labels, or investment ranking.

