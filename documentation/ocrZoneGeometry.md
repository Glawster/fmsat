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

## Team Instructions anchor contract

Team Instructions extraction is deliberately local rather than screen-relative.
The stable evidence chain is:

1. locate the `Team Instructions` breadcrumb;
2. locate the `In Possession` and `Out of Possession` labels below it;
3. use the label spacing to establish the local modal scale and orientation;
4. detect the active phase from the underline in that local frame; and
5. project the configured six-column card grid into that frame.

This means moving the FM window on the desktop, supplying a larger screenshot or
supplying a screenshot already cropped to the Team Instructions modal must not
move the instruction OCR zones. Whole-screen percentage geometry is retained
only as a legacy fallback when the stronger breadcrumb/tab evidence cannot be
recovered.

A 2026-08-16 regression demonstrated why this contract matters. A 1505-pixel-wide
already-cropped modal was incorrectly passed through the old `x=0.205`,
`width=0.590` fallback. Its effective reference frame therefore began about 308
pixels into the modal. Each category subsequently read text from the following
card (`passingDirectness` read the tail of `Tempo`, `tempo` read `Time Wasting`,
and the same displacement occurred Out of Possession). The active-tab underline
was also outside the erroneous local frame. Tests now reproduce the 1505x895 In
Possession and 1505x652 Out of Possession capture shapes and require the visible
tab anchors to win over that fallback.

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

Different FM layouts and different reference-frame modes must not be mixed into
one statistical baseline. In particular, anchor-relative Team Instructions
geometry should be compared with other anchor-relative observations rather than
with old whole-screen fallback geometry.

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

`tests/test_tacticLayoutAnchor.py` separately protects the anchor behaviour,
including cropped Team Instructions captures. A change that reintroduces the
whole-screen fallback when the breadcrumb and both phase labels are visible is a
regression even if OCR happens to return some text.

The historical classifier and persistence tests verify bootstrap behaviour,
normal variation, drift, anomaly detection and exclusion of anomalous or
unvalidated observations from the learned baseline.

## Current integration boundary

Anchor-relative Team Instructions frame recovery is now preferred over the
whole-screen percentage fallback. The history and classification layer is also
available for tactic extraction.

The remaining extraction wiring step is to record the effective anchor-derived
panel and card geometry from each successful tactic screenshot run and surface
`ocrZoneDrift` diagnostics when a new observation is anomalous. This work remains
prioritised before the next squad-analysis increment because dependable OCR
evidence is a prerequisite for dependable role-fit analysis.
