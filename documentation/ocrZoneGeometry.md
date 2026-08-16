# OCR zone geometry history

FMSAT treats tactic OCR geometry as evidence that can be measured over time rather
than as an unchecked set of coordinates.

## Purpose

The tactic extractor uses normalized `x`, `y`, `width` and `height` values so
screen resolution and desktop position do not by themselves move a recognition
zone. Even with normalized coordinates, a bad breadcrumb, panel anchor or layout
profile can shift the effective OCR reference frame and make previously reliable
instruction regions miss their cards.

The geometry history provides two protections:

1. regression tests lock the currently accepted normalized formation and
   instruction-zone configuration; and
2. an append-only historical store allows newly observed geometry to be compared
   with previous validated observations for the same screen, layout profile and
   zone.

## Observation identity

Only comparable observations belong in one history. Each observation therefore
records:

- screen type;
- layout profile;
- zone name;
- normalized `x`, `y`, `width` and `height`;
- classification;
- whether the observation is accepted as baseline evidence;
- source import session where available; and
- observation time.

Different FM layouts such as the compact two-pitch planner and the wide planner
with squad panel must not be mixed into one statistical baseline.

## Drift classification

FMSAT uses robust statistics rather than a permanently fixed pixel tolerance.
For each coordinate component the classifier calculates the historical median
and median absolute deviation (MAD). The maximum robust deviation across
`x`, `y`, `width` and `height` determines the state:

- `unavailable` — there are not yet enough accepted historical observations;
- `normal` — geometry is within the normal historical variation;
- `drifting` — movement is unusual but still within the configured warning
  range; and
- `anomalous` — movement is well outside historical behaviour.

A small minimum statistical scale prevents a history containing identical values
from treating harmless floating-point differences as infinite drift.

## Learning safety

Historical learning is deliberately conservative.

A validated observation may become baseline evidence while the history is being
bootstrapped and when it is classified as `normal` or `drifting`. An anomalous
observation is retained so the change can be diagnosed, but it is never accepted
as baseline evidence automatically. An unvalidated observation also never enters
the baseline.

This prevents a sequence of bad OCR runs from gradually teaching FMSAT that bad
geometry is normal.

## Regression contract

`tests/test_ocrZoneHistory.py` contains an explicit contract for currently
accepted FM26 tactic geometry. Intentional recalibration therefore requires an
explicit test change rather than silently moving the recognition zones.

The historical classifier and persistence tests separately verify bootstrap
behaviour, normal variation, drift, anomaly detection and exclusion of anomalous
or unvalidated observations from the learned baseline.

## Current integration boundary

The history and classification layer is now available for tactic extraction.
The next extraction wiring step is to record the effective anchor-derived panel
and card geometry from each successful tactic screenshot run and surface
`ocrZoneDrift` diagnostics when a new observation is anomalous. This work is
being prioritised before the next squad-analysis increment because dependable OCR
evidence is a prerequisite for dependable role-fit analysis.
