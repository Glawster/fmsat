# OCR zone geometry history

FMSAT treats OCR geometry as evidence that can be measured over time rather than
as an unchecked set of coordinates.

## Purpose

The tactic extractor uses normalized `x`, `y`, `width` and `height` values so
screen resolution and desktop position do not by themselves move a recognition
zone. Even with normalized coordinates, a bad breadcrumb, panel anchor or layout
profile can shift the effective OCR reference frame and make previously reliable
regions miss their content.

The geometry history provides two protections:

1. regression tests lock the currently accepted normalized fallback geometry; and
2. an append-only historical store allows newly observed geometry to be compared
   with previous validated observations for the same screen, layout profile and
   zone.

## Reference-frame rule

Every primary OCR path must establish the smallest reliable local reference frame
from visible evidence before applying child regions. A configured screen-relative
rectangle may remain as a fallback, but it must not replace a stronger local
anchor that is present in the capture. An image that is already the local reference
frame must never be cropped a second time.

The current OCR paths are handled as follows:

- **Team Instructions** — breadcrumb and phase-tab anchored; already-cropped modal
  captures are retained whole.
- **Formation** — the layout anchor retains the complete Tactics Planner capture;
  the wide/compact profile supplies horizontal pitch placement only, while FM26
  refines the vertical pitch extent from the visible green field. This prevents a
  calibrated short region from truncating defenders and the goalkeeper row.
- **Squad Attributes** — geometry-capable OCR runs against the full image and
  derives columns/rows from the observed `Player`, `Position`, `CA`, `PA` and
  attribute headings. YAML row/column geometry is legacy fallback for OCR engines
  without positional geometry.
- **Role Profile** — OCR runs against the complete image and sections are derived
  from semantic headings such as `Role Ability`, `Key Attributes` and
  `Player Instructions`; no fixed child grid is the primary parser.
- **Formation metadata** — mentality is searched semantically across whole-image
  OCR rather than from a fixed crop.
- **Tactic selector name** — the importer retains its small configured header crop
  because that crop is itself the visible selector control, and tactic identity is
  subsequently owned/editable by FMSAT. It must not be reused as a parent frame
  for Formation or Team Instructions extraction.

This audit is intended to prevent a fix in one OCR path from leaving another path
with the same reference-frame defect.

## Team Instructions anchor contract

Team Instructions extraction is deliberately local rather than screen-relative.
The stable evidence chain is:

1. locate the `Team Instructions` breadcrumb;
2. when that breadcrumb is already close to the capture's top-left edge, treat
   the capture itself as the modal reference frame and never crop it a second time;
3. otherwise locate the `In Possession` and `Out of Possession` labels below it;
4. use those local anchors to establish the modal frame;
5. detect the active phase from the underline in that local frame; and
6. project the configured six-column card grid into that frame.

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
Possession and 1505x652 Out of Possession capture shapes and require the complete
modal to be retained even when OCR does not recover both tab labels.

## Formation pitch contract

Formation uses the complete anchored Tactics Planner capture as its parent frame.
The two calibrated layout profiles still distinguish the horizontal placement of
the pitches in compact and wide Planner layouts, but their configured `y` and
`height` values are fallback evidence only.

FM26 pitch refinement samples the configured horizontal pitch corridor, identifies
the visible green field and expands the phase region through its observed vertical
extent. The detected extent is accepted only when it occupies at least half of the
capture, begins in the expected Planner body and reaches the lower portion of the
window. Otherwise the calibrated profile is retained unchanged.

This protects against the 2026-08-17 regression where a wide Planner profile ended
near the midfield/DM area and excluded the CB/GK rows even though the outer
Tactics Planner anchor was correct.

## Player-agnostic tactic evidence

Players displayed on the FM Tactics Planner are incidental evidence about the
current selection, not part of the tactic definition. FMSAT may retain the text
for provenance and diagnostics, but duplicated or misread player names/numbers
must not make a tactic invalid. In particular, an `ambiguousPhaseLink` caused by
a player such as `10 Sibley` appearing more than once is ignored by structured
tactic validation. Tactical phase linkage and validation remain based on slot
geometry, positions and roles rather than squad identity.

## Observation identity

Only comparable observations belong in one history. Each observation therefore
records screen type, layout profile, zone name, normalized geometry,
classification, baseline acceptance, source import session where available and
observation time. Different FM layouts and reference-frame modes must not be
mixed into one statistical baseline.

## Drift classification

FMSAT uses robust statistics rather than a permanently fixed pixel tolerance.
For each coordinate component the classifier calculates the historical median
and median absolute deviation (MAD). The maximum robust deviation across
`x`, `y`, `width` and `height` determines the state:

- `unavailable` — there are not yet enough accepted historical observations;
- `normal` — geometry is within normal historical variation;
- `drifting` — movement is unusual but within the warning range; and
- `anomalous` — movement is well outside historical behaviour.

## Learning safety

A validated observation may become baseline evidence while history is being
bootstrapped and when classified as `normal` or `drifting`. An anomalous or
unvalidated observation is retained for diagnosis but never teaches the baseline
automatically.

## Regression contract

`tests/test_ocrZoneHistory.py` locks the accepted fallback geometry.
`tests/test_tacticLayoutAnchor.py` protects Team Instructions reference-frame
anchoring, including already-cropped modals and active underline recognition.
`tests/test_tacticFormationFm26.py` protects visible-field Formation depth and
requires a safe fallback when the field cannot be established.

## Current integration boundary

Anchor-relative Team Instructions frame recovery and visible-field Formation depth
are preferred over whole-screen percentage fallbacks. Squad Attributes, Role
Profile and Formation metadata already derive their primary structure from OCR
geometry or semantic headings. The history/classification layer remains available;
the remaining integration step is to record effective anchor-derived panel/card
geometry from each successful run and surface `ocrZoneDrift` diagnostics when a
new observation is anomalous.
