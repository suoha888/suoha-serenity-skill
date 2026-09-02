# Provenance Contract

All distilled knowledge and all material report claims must be replayable:

~~~text
method card / thesis event
  -> claim
  -> evidence
  -> original source ID and locator
  -> published_at / captured_at / known_at / as_of
  -> content hash and extraction version
~~~

## Minimum requirements

- Stable IDs for every record, claim, evidence object, relation, thesis event,
  and method card.
- Original source ID and URL or local locator.
- Immutable content hashes for imported material.
- Adapter and extraction version.
- Thread, reply, quote, and parent relationships when available.
- Human review status for every distilled object.
- Separate outcome/calibration data that cannot alter historical objects.

If any chain link is missing, lower confidence and use UNKNOWN or
NOT_ESTABLISHED. Never repair provenance from memory.

Social posts are lead evidence. A material current-company claim should be
verified with a stronger source where one is available.
