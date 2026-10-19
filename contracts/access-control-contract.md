# Access-Control Contract

Access labels are taints, not descriptive tags. Every derived object inherits
the most restrictive access level of all its inputs.

## Levels

| Level | Meaning | May enter public repository? |
|---|---|---:|
| public | User-owned or openly distributable project material | Yes, if rights are clear |
| subscription | Paywalled or exclusive source material | No |
| private | User-local material or private research | No |
| synthetic | Project-authored test fixture with no third-party payload | Yes |

## Propagation

~~~text
derived.access_level = max_restriction(input.access_level)
~~~

The following are all derived objects and retain the restriction:

- normalized records;
- context packs;
- claims and evidence excerpts;
- relations and entity links;
- thesis events;
- method cards;
- summaries, prompts, reports, indexes, and exports.

Never merge public and subscription records into normalized/all.jsonl.
Subscription-derived method cards are still subscription-restricted even when
the prose has been rewritten.

## Publication boundary

The public source repository may contain code, schemas, contracts, abstract
method descriptions, synthetic examples, and evaluation harnesses. It must not
contain raw archives, screenshots, subscription text, subscription summaries,
or reversible derivatives.

Local scripts must fail closed when a partition label is missing, inconsistent,
or downgraded.
