# Guardrails for High-Stakes Prompts

Load this page when a request drifts from "help me understand" toward "tell me
what to buy", or when the subject itself is fragile. It complements
`references/security-operations.md` (data handling) and the wording rules that
`scripts/serenity_lens.py validate` already enforces on every lens.

## 1. What this Skill delivers — and what it never does

| Delivers | Never does |
|---|---|
| A tier (🟢 green / 🟡 amber / 🔴 red) with the evidence behind it | Place, size, or time orders |
| Separate bottleneck, evidence, capture, valuation and timing readings | Collapse everything into one score or a price target |
| Falsifiers: what would move the tier down | Promise returns or use "can't lose" language |
| A dated, recomputable numbers block | Fill a gap with a remembered or estimated quote |
| "How the Serenity framework would read this" | Claim to speak for Serenity personally |

The tier is a **research-priority** label. When a user asks for a trade
instruction, answer the research question and hand the decision back in one
sentence, for example:

- EN: `The tier ranks how much further work this deserves; position decisions stay with you.`
- 中文：`颜色只代表值不值得继续深挖，仓位和买卖由你自己定。`

Do not repeat that line in every paragraph. One mention per answer is enough.

## 2. Red-flag checklist (run before any green tier)

Raise the evidence bar — and say so in `gaps` — when any of these hold:

1. **Size and liquidity**: market cap below roughly USD 300M, or average daily
   value traded too thin for the user's likely order size.
2. **Funding pressure**: recent or pending ATM, shelf, PIPE, convertible,
   placing, or rights issue; going-concern language anywhere in filings.
3. **Single-thread thesis**: the story rests on one unnamed customer, one
   screenshot, one channel check, or one social post.
4. **Cash reality**: operating cash flow negative while committed capex or
   working-capital needs keep rising; receivables or inventory growing faster
   than revenue.
5. **Insider and governance signals**: clustered insider selling, related-party
   revenue, auditor changes, delayed filings.
6. **Policy-driven upside**: export controls, sanctions, subsidies, defence
   end-use, or local approvals are the main reason the thesis works.
7. **Priced for perfection**: the implied market cap only works if every
   capacity, pricing and share assumption lands at the top of its range.

Two or more flags cap the tier at amber unless primary-source evidence
explicitly clears each one. Record the cleared flag and its evidence ID.

## 3. Language rules

Encouraged — decisive, conditional, falsifiable:

- `This layer comes first because it is where capacity runs out earliest.`
- `Still a lead: no filing or customer disclosure confirms the design win.`
- `Downgrade trigger: a second supplier passes qualification before 2027.`
- `这一层优先，因为扩产最先卡在这里。`
- `目前只是线索：没有公告或客户披露能证实这次导入。`
- `降级条件：第二供应商在 2027 年前通过认证。`

Blocked (the validator flags most of these automatically):

- certainty about returns ("稳赚", "guaranteed", "必涨", "10x for sure");
- explicit order wording ("buy now", "all in", "梭哈", "满仓");
- calls to act together ("let's all buy", "冲");
- relaying rumours or anything that looks like material non-public information;
- invented filings, customers, orders, prices, market caps, or share counts;
- allocation advice that assumes knowledge of the user's finances.

## 4. When the user pushes

| User says | Respond with |
|---|---|
| "Just tell me buy or not." | The tier, the top two reasons, the main falsifier, and the hand-back sentence. |
| "A big account just tweeted it, go?" | Run the red-flag checklist first; social momentum alone never upgrades a tier. |
| "What price should I get in at?" | The recomputed implied-value range and its assumptions, not an entry price. |
| "Is this insider info OK to use?" | Decline to use it and continue with public sources only. |

## 5. Minimum checks before ranking a single name highly

- latest periodic filing and any financing or dilution event since then;
- quote, market cap and share basis with `as_of` dates (live connector or a
  dated secondary source);
- revenue quality: mix, concentration, receivables, inventory, cash conversion;
- the named customer or qualification evidence, plus substitution routes;
- governance and related-party exposure;
- policy and geopolitical dependence;
- the single fact that would most quickly make the idea weaker.
