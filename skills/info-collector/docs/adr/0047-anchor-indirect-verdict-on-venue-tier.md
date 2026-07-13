# ADR 0047: anchor indirect-verdict on venue tier, not agent source_type label

## Context

The DeepSeek retrospective found a `‡` (indirect) misjudgment: the V3 technical
report (an arXiv paper, Tier 1) was tagged `source_metadata.source_type: vendor_benchmark`
and marked indirect, while sibling arXiv reports (V2, R1) stayed confirmed — an
inconsistency driven purely by a mislabel.

Root cause: `_is_indirect_source` (claim_validator.py) flips any `vendor_benchmark`
+ `exact`/`range` claim to indirect regardless of the source venue. `source_type`
is agent-supplied metadata describing benchmark provenance; it is not a proxy for
the venue's authority. An authoritative venue (Tier 1–2) mislabeled as
`vendor_benchmark` was being wrongly downgraded.

## Decision

The `vendor_benchmark` → indirect flip now applies **only when the source venue is
itself non-authoritative** (tier ≥ 3). A claim whose sources include any Tier 1–2
venue is never flipped on the strength of a possibly-wrong `source_type` label.

Authority is therefore anchored on the source's `source_tier` (already collected),
not on the free-text label the agent wrote. `source_type` retains its role of
flagging vendor self-benchmarks among non-authoritative venues.

## Consequences

- Fixes the arXiv `‡` inconsistency without special-casing arxiv.org by domain.
- A genuine vendor benchmark hosted on a Tier 2 site (e.g. a vendor's GitHub with
  their own bench) is no longer auto-flagged indirect. This is accepted: such cases
  are rare and `vendor_affiliation` remains available for manual signaling.
- Glossary now splits `source_type` (benchmark provenance) from venue authority to
  stop the original conflation.

## Status: accepted
