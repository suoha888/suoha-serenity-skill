# Where to Look, Market by Market

Use this page to pick the primary-source route for a listing venue and to
decide what counts as "data unavailable". The live connector
(`connectors/live_data.py` + `connectors/venues.py`) covers quotes, FX and SEC
filings, and — for Asian listings — CNINFO, HKEXnews, TDnet, TWSE/TPEx monthly
revenue, EDINET/DART (optional free keys) and a second-source quote
automatically, plus A-share / Hong Kong statements from an aggregator
(section E); everything else on this page is a manual or host-tool route.

## A. Identity and numbers block (all venues)

Resolve these before any ranking, and keep each field with its own
`as_of` date, source, and status (`OK` / `STALE` / `UNKNOWN` / `UNAVAILABLE`):

| Field | Rule |
|---|---|
| Legal issuer, ticker, venue, share class | Multi-class issuers (e.g. Korean preferred lines, dual US classes) must state which lines are included in market cap. |
| Quote and quote currency | Minor units are normalised (GBp/GBX → GBP ÷ 100, ZAc → ZAR ÷ 100); never compare a pence quote with a pound value. |
| Shares and share basis | Basic, diluted, and weighted-average shares are not interchangeable; name the basis. ADRs need the ADR-to-ordinary ratio (`--adr-ratio`). |
| Market cap and basis | Keep the reported value; recompute it with `serenity_lens.py compute` rather than typing it. |
| FX | Cross-currency comparisons carry a dated FX item (`live_data.py fx`). |

An old quote is `STALE`; a missing one is `UNKNOWN`. Neither may be replaced by
a remembered figure. Any timestamp later than the research cutoff is unusable.

## B. Fallback ladder before declaring a field unavailable

1. `live_data.py snapshot|quote` (or a host market-data tool already present).
2. The exchange's or issuer's own quote/history page for the cutoff date.
3. One independent, reputable dated source — required when venue, session,
   currency, price, or share count disagree between routes.

Log every attempt: route, retrieval time, session (regular / extended /
unknown), delay, and what came back. A vendor "last" is not an official close,
and a working quote does not validate that vendor's share count, market cap,
or multiples. If a tool returns no URL, cite the tool name plus retrieval
time — never invent a link. After three distinct failures, stop and list the
unresolved field instead of retrying the same empty page.

## C. Venue routes

| Venue | Primary filings and disclosures | Corroboration | Venue-specific checks |
|---|---|---|---|
| **United States** (SEC) | 10-K, 10-Q, 8-K, 20-F/6-K for foreign filers, S-1/S-3/424B, DEF 14A, Forms 3/4/5 — fetched by `live_data.py filings` / `filing-text` / `fts` | Call transcripts, IR decks, counterparties' filings, patents, standards bodies | Shelf/ATM capacity, converts, SBC dilution, customer-concentration footnotes, backlog/RPO, short interest |
| **Mainland China** (SSE/SZSE/BSE) | 定期报告（年度、半年度、季度）；临时性公告；问询函及公司回复；监管措施 | 投资者互动平台问答（深交所、上交所）；招标与中标公示；环评、能评与项目备案；进出口统计；用供应商和客户的公开披露互相印证 | 应收与存货增速、合同负债与经营性现金流、在建项目何时转为固定资产、关联方交易、定增/可转债/质押、商誉、补贴依赖 |
| **Hong Kong** (HKEX) | HKEXnews announcements, annual/interim reports, circulars on placings, connected transactions, and convertibles | Mainland regulator documents for China-heavy businesses, company presentations | Free float and spread, refinancing walls, connected-party governance, Stock Connect status |
| **Taiwan** (TWSE/TPEx) | MOPS filings including **monthly revenue** reports, annual reports, material-information notices | IR decks, customer/supplier cross-checks, trade press | Month-over-month revenue inflections, customer concentration, TWD sensitivity, cross-strait risk, qualification calendars |
| **Japan** (TSE) | TDnet timely disclosures, 決算短信, securities reports (EDINET), integrated reports | Segment tables, trade journals, industry associations | Conservative guidance habits, JPY sensitivity, cross-shareholdings, thin analyst coverage |
| **Korea** (KRX) | DART filings, quarterly reports, fair-disclosure notices | Monthly export statistics, customer-ecosystem disclosures | Preferred vs common lines, memory-cycle exposure, chaebol customer dependence, KRW moves |
| **UK / Europe** | RNS (London) and national exchange ad-hoc releases, annual reports | EU/IPCEI grant documents, partnership releases, standards bodies | Liquidity, GBp quoting, grant dependence, language/translation risk |
| **Other venues** | The exchange's official disclosure system first | Local trade press, customs or industry statistics | Mark `sec_filings_not_applicable_non_us` and do not treat missing SEC data as missing evidence |

## D. Non-US issuers and the live connector

For non-SEC issuers the connector returns quote, FX and summary fundamentals,
sets `filings.status = unavailable` with a non-US reason, and attaches an
`exchange` block (`python suoha.py exchange <SYMBOL>`):

| Venue | Automatic route | What it gives | Limits |
|---|---|---|---|
| Mainland China (`.SS/.SZ/.BJ`) | CNINFO announcement search + Tencent quote | Titles, dates and PDF links (E-LIVE-XCH-nn); second-source price, total shares | Titles only; open the PDF before citing a number |
| Hong Kong (`.HK`) | HKEXnews title search + Tencent quote | Same as above | Placing / connected-transaction details live in the circular |
| Taiwan (`.TW/.TWO`) | TWSE / TPEx OpenAPI | Latest monthly revenue with YoY, MoM, YTD YoY (E-LIVE-MREV) | No free announcement API — read MOPS for material information |
| Japan (`.T`) | TDnet; EDINET with `EDINET_API_KEY` | Timely disclosures (about the last 31 days), statutory filings | TDnet keeps a short window; older items need EDINET or IR |
| Korea (`.KS/.KQ`) | DART with `DART_API_KEY` | Filing list | Without a key: manual DART route |
| Others | — | `no_connector` with the system name to read | Manual route from section C |

Announcement titles are matched against multilingual keyword families
(dilution, insider/holder change, major contract, guidance, listing or
going-concern risk, debt issuance, buyback, capacity/capex). A flag is a prompt
to open the document, never a conclusion. Two quotes that disagree by more than
1.5% raise `quote_cross_check_mismatch` — resolve session, currency or share
line; never average them. An exchange-side share count more than 3% away from
the reported count raises `share_count_vs_exchange_±x%`.

An empty window is still a result: "no items in the last N days" is reported
as such, not as missing data.

## E. A-shares and Hong Kong: statements, names and A+H (v7.1)

| Need | Automatic route | Primary source to confirm | Notes |
|---|---|---|---|
| Name or code → symbol | `assets/universe/{cn,hk,us,ah}.json` built by `python connectors/universe.py build` from CNINFO `szse_stock.json`, HKEXnews active-stock lists (zh/en) and SEC `company_tickers_exchange.json` | The exchange listing page | Dated (`as_of`); rebuild monthly. Contains-matches return `review_needed=true`. |
| Statements (8–10 periods), TTM, single-quarter figures | Eastmoney F10 datacenter (`connectors/cnhk_fin.py`, `E-LIVE-FIN-CN/HK`) | CNINFO / HKEXnews periodic reports | Aggregator: `financials_from_aggregator` is always raised. TTM = latest YTD + prior FY − prior-year YTD. |
| Balance sheet (cash, borrowings, receivables, inventory, contract liabilities, goodwill) | Same (`E-LIVE-BAL-CN/HK`); A-share financial-template companies skipped | Same | Year-ago pair for working-capital checks. |
| HK reporting currency | Yahoo quarterly revenue cross-check | Annual report cover | The provider's currency field for HK is the trading currency; `hk_reporting_currency_unconfirmed` when Yahoo cannot confirm. |
| Share pledge (A-shares) | China Securities Depository list (`E-LIVE-PLEDGE`) | CSDC weekly data | No HK equivalent. |
| Dividends | A-share dividend plan table (`E-LIVE-DIV`); HK latest fiscal-year DPS | Results announcement | Yield uses the current price. |
| A/H premium | Tencent quotes for both lines + Yahoo HKD/CNY (`E-LIVE-AH`) | Exchange quotes | Positive = A line richer. Value each line at its own price; per-share ratios use total shares. |
| Bank asset quality | Provider NPL, provision coverage, CET1, capital adequacy | Bank's periodic report (Pillar 3 section) | Only for `bank` routing. |

`aggregator_vs_yahoo_revenue_mismatch` (>5%) means the two disagree on the
same period: check period end, consolidation and currency before using either
(for financials the warning is `definition_differs` — banks and insurers
define revenue differently). `local_financials_older_than_200_days` means the
latest period is stale. The datacenter endpoint is unofficial and may change
or rate-limit; on failure the snapshot keeps Yahoo fundamentals and records
`local_financials_unavailable`.
