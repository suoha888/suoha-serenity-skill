# Deep Research Workflow

Use this file when the user asks for current opportunities, ranked candidates, "which is worth researching now", or a full theme scan.

## Goal

Turn a broad investment theme into a ranked set of research priorities backed by current sources.

The final answer should read like a clear research conversation. The internal workflow can be rigorous; the external answer should stay plain and useful.

## Minimum completion standard

For a current theme scan, aim to complete these checks before the final answer:

- cover at least three value-chain layers;
- rank the scarce layers before ranking companies;
- inspect at least 25 sources when tools and runtime allow;
- build a starting candidate universe of at least 20 companies when the market is broad enough;
- build a candidate universe across visible winners, upstream suppliers, equipment, materials, testing, infrastructure, and adjacent beneficiaries;
- identify the strongest scarce layers;
- select the top 3-7 priorities;
- explain what each final candidate constrains or sits closest to;
- support each top candidate with concrete evidence;
- state what could make the judgment wrong;
- name at least one obvious or popular area that ranked lower and explain why;
- give the next checks the user should run.

If tools or time prevent that standard, state the limitation and give a focused partial answer with an exact verification path.

## Workflow

### 1. Scope the request

Infer the missing parts when reasonable:

- market: US, Hong Kong, A-share, Taiwan, Japan, Korea, Europe, global;
- theme: AI infrastructure, semiconductors, CPO, advanced packaging, robotics, power, cooling, materials, equipment, healthcare manufacturing, defense electronics;
- time window: for "now" use 3-12 months as the default research window;
- output: priority research candidates, reasoning, and next checks.

Ask a clarification only when the missing scope would materially change the answer.

### 2. Convert the theme into a system change

Write the practical chain:

`demand wave -> system pressure -> required technical change -> architecture necessity -> constrained layer`

Examples:

- AI clusters -> bandwidth and power pressure -> optical interconnect and switching upgrades -> lasers, DSP/ASICs, testing, packaging, substrates.
- AI servers -> power density and uptime pressure -> power conversion, transformers, switchgear, liquid cooling -> qualified equipment and components.
- Humanoid robotics -> actuator and sensing density -> precision reducers, motors, encoders, tactile sensing, batteries -> manufacturing yield and supplier qualification.

### 3. Build the value-chain map

Use these layers as a checklist:

1. End customers and capex source.
2. System integrators and OEMs.
3. Modules and subsystems.
4. Chips, devices, and critical components.
5. Process, assembly, packaging, and testing.
6. Equipment and metrology.
7. Materials, consumables, and specialty inputs.
8. Physical infrastructure.

### 4. Test architecture necessity and search for scarce layers

A scarce layer becomes interesting only after an architecture test and several
additional signals stack:

- the proposed system architecture cannot bypass it without a material redesign,
  performance loss, or qualification delay;
- customers cannot scale without it;
- supplier count is low;
- qualification is slow;
- expansion requires specialized equipment, permits, know-how, or material purity;
- customers show urgency through prepayments, capacity reservations, long-term contracts, expedited orders, or price acceptance;
- the public market still classifies the company by an older business category.

Record the supply-chain edge (both endpoints, product/process, relationship
type, effective period, alternatives, evidence, and counterevidence). Then write
the layer ranking before moving to the final company list.

Example:

```text
I would rank the layers first: equipment platforms, process-specific equipment, compute chips, advanced packaging materials, then broad component suppliers.
Equipment platforms and process-specific tools sit closer to fab expansion and technology migration. Broad component suppliers usually need stronger order and margin evidence to rank higher.
```

Chinese:

```text
先排产业链层级：设备平台、关键工艺设备、国产算力芯片、先进封装材料、普通零部件。
前两层更接近晶圆厂扩产和工艺升级的硬约束，后面几层需要更强的订单和财务证据才能往前排。
```

### 5. Build the company universe

Include names across the chain before ranking. Avoid starting from popular tickers.

For broad market scans, start with at least 20 candidates when the market has enough listed companies. Cover:

- obvious leaders;
- compute chips and AI accelerators;
- EDA, IP, verification, and design infrastructure;
- memory, storage, and interconnect chips;
- upstream equipment;
- process-specific tools;
- materials and consumables;
- testing and metrology;
- advanced packaging and OSAT;
- PCB, CCL, optical links, and server infrastructure when the theme reaches AI servers;
- infrastructure and power;
- lower-priority or popular names that need explicit downgrading.

Keep categories clean. Split a broad bucket when companies have different economics, evidence paths, or bottleneck logic. For A-share AI semiconductors, avoid merging compute chips, EDA/IP, memory interconnect, equipment, materials, OSAT, optical links, and PCB/CCL into one candidate layer.

Classify each candidate in plain language:

- controls the scarce layer;
- supplies the scarce layer;
- benefits from demand but has limited control;
- has exposure with weak pricing power;
- has a good story with weak proof.

### 6. Gather current evidence

Prioritize:

- filings and exchange disclosures;
- company announcements and investor relations materials;
- earnings transcripts and presentations;
- official customer/order/project/regulatory documents;
- patents, standards, technical papers, and trade publications;
- reputable financial and industry media;
- specialist analysis as context;
- social posts as leads.

Use `references/evidence-ladder.md` for grading.

For every shortlisted company, create a CompanyProfile before making a market
judgment. Resolve the legal entity, ticker, exchange, share class, quote
currency, business model, segment/revenue mix, customer exposure, geography,
competitors, financial quality, main risks, direct exposure, economic capture,
and capital structure. Each field gets its own dated source or is explicitly
`UNKNOWN`.

Create a MarketSnapshot separately for price, price type, market cap, shares,
share basis, currency, `price_as_of`, `market_cap_as_of`, source, and freshness.
An old quote is `STALE`, not “current”. A calculated market cap preserves both
the price and share-count evidence and does not silently replace a reported
value.

For deep current scans, aim for 25+ sources before the final ranking. A good mix:

- 10+ filings, exchange disclosures, annual reports, quarterly reports, or announcements;
- 5+ company IR/transcript/product/technical sources;
- 5+ credible media, trade publications, industry association, patents, standards, or project records;
- extra sources for cross-checking valuation, liquidity, financing, and customer evidence.

### 7. Translate value capture and market expectations

For each top candidate, walk the validation ladder in order:

```text
architecture necessity -> physical supply -> customer validation
-> company capture -> financial transmission -> market expectations
```

Then connect the scarce layer to the company’s actual
business model: capacity manufacturer, equipment, consumables/materials,
IP/royalty, project/infrastructure, or diversified. Separate industry growth,
company revenue, margin, cash flow, funding, dilution, and per-share economics.

If a social post or influential public source is part of the lead, run the
reflexivity audit. A post-first price move is non-independent evidence until
independent fundamentals confirm the mechanism.

Then state the variant-perception hypothesis:

```text
market proxy -> what appears priced -> overlooked mechanism -> measurable bridge
```

Write every research reason as `IF / THEN / BECAUSE / CONFIRM WITH / FAIL IF`.
This explains why a candidate may deserve more research without pretending that
the evidence is a guaranteed buy signal.

### 8. Rank candidates

Rank by:

- demand pressure;
- tightness of the scarce layer;
- supplier concentration;
- expansion difficulty;
- evidence strength;
- valuation gap or market misunderstanding;
- near-term events that could change investor perception;
- financing, governance, liquidity, accounting, and geopolitical risk.

Use `scripts/serenity_scorecard.py` only as a non-additive dimension report.
Never sum bottleneck, evidence, valuation, catalyst, and risk into one score.

Keep two rankings distinct:

1. **Layer ranking**: which parts of the system deserve attention first.
2. **Company ranking**: which companies best represent those layers with evidence.

This keeps the answer from becoming a generic list of popular stocks.

For each final company, answer:

- What exactly does it constrain?
- Where does it sit in the chain?
- Why does it rank here?
- What evidence supports that rank?
- What would make the rank weaker?

### 9. Explain the answer

The answer should start with the conclusion:

- the layers worth prioritizing;
- the top names to research first;
- the reason those names rank higher;
- the strongest proof;
- the popular areas that ranked lower;
- the main ways the view can be wrong;
- the next checks.

Prefer normal prose. Add a compact table only for rankings or evidence comparison.

## Mainland China scans

Take the source route and the venue checks from the mainland row of
`references/market-source-playbook.md` §C. Two habits matter most here:
reconcile the story against receivables, inventory, contract liabilities and
operating cash flow before ranking, and read inquiry-letter replies — they
often contain the customer and capacity detail the annual report leaves out.

Write the conclusion the way a practitioner talks, for example:

- `带宽和工艺先卡住，算力芯片本身反而排后面。`
- `我先排层级再排公司，第一层是……`
- `它靠前，因为扩产最先卡在它手里的环节。`
- `这条热门线我先往后放，原因是……`
- `这个判断最可能错在……`
