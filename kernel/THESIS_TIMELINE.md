# Thesis Timeline

Historical material should be represented as dated state changes rather than a
static list of tickers or a single rewritten thesis document.

## Event vocabulary

Use these event types in `ThesisEvent` records:

- `establish`: first explicit version of a thesis;
- `reinforce`: new evidence strengthens the existing thesis;
- `revise`: an assumption, scope, or confidence changes;
- `reverse`: the stance changes direction;
- `invalidate`: a required mechanism or claim is rejected;
- `risk_added`: a material risk is newly identified;
- `catalyst_failed`: an expected observable event did not occur.

## Temporal rules

Record what was knowable at the event time, not what became obvious later.
Keep original post IDs, timestamps, thread/quote relationships, extraction
version, and review status. Later prices and outcomes belong in a separate
calibration record and must not rewrite the historical event.

Store both `event_at` (when the stance or source event occurred) and `known_at`
(when the system was allowed to know it). Historical replay filters on
`known_at`, not on the time when the archive was later imported.

Each event links to the claims and evidence that caused the state transition.
If the transition cannot be supported, keep the event as a tentative extraction
or mark it `unknown`; do not infer conviction from engagement or a ticker mention
alone.

## Review questions

For every material change, answer:

1. What was the previous thesis state?
2. What new evidence was available then?
3. Which assumption changed?
4. What is the new state and confidence?
5. What future observation would confirm or invalidate it?
