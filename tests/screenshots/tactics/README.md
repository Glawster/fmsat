# Tactic screenshot regression fixtures

These screenshots are canonical regression evidence for tactic capture and UI testing.

Each fixture directory contains exactly three immutable Football Manager screenshots:

- `formation.png`
- `inPossession.png`
- `outOfPossession.png`

Current fixture identities:

- `highPress`
- `highPress2`
- `libero1974`
- `liberoWealdstone`

Do not edit or replace a screenshot simply to make a test pass. If Football Manager evidence changes, add or deliberately replace a fixture only after reviewing the new screenshots and updating the corresponding expected fixture data.

Reviewed expected data lives under `tests/fixtures/tactics/` and is the asserted truth for the visible evidence. It must not be generated from the code under test.

The intended regression chain is:

`screenshots -> extraction -> persisted tactic -> object model -> tactic UI`

The same unchanged screenshot set must regenerate to the same structured tactic model every time. Repeated regeneration must therefore be idempotent. A second regeneration producing different roles, slot linkage or instructions is a regression.

The UI regression tests should assert what the user sees, including phase-role ordering and selected instruction values, rather than only asserting internal model counts.

Squad fixtures follow the same principle separately and use two outfield squad screenshots plus one goalkeeper-specific screenshot per canonical squad fixture.
