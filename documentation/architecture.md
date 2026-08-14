# Architecture

FMSAT keeps Qt at the outer edge. `MainWindow` invokes `ScreenshotImportService`, which
coordinates preprocessing, screen detection, OCR, tactic-name extraction and Squad
Attributes parsing. Parsers receive an `OcrEngine` interface, so PaddleOCR can be replaced
without UI or database changes.

`WelcomeView` is the default `MainWindow` page. It receives existing application actions
for imports and uses `WelcomeService` to request bounded tactic and squad records from the
database gateway. It contains no OCR, parsing, raw SQL or persistence logic. The editable
player review table remains on a separate stacked page and is shown only while reviewing a
squad import.

Workspace rows open the existing management UI in a focused tactic-editor or squad-editor
presentation with the selected record active. Applying a tactic is owned by the tactic
editor; persisted squad cleanup is owned by the squad editor. `MainWindow.dataChanged` is
the central Qt signal used to refresh workspace summaries after imports and editor changes.

YAML owns screen regions, preprocessing switches, detection keywords and attribute
definitions. SQLite writes are performed through a transactional SQLAlchemy gateway.
The tactic name is confirmed or corrected before persistence. The review table converts
squad OCR output back into core data objects only after user edits.

Tactics own their three tactic captures. Squads own Squad Attributes imports and player
snapshots independently; no single-tactic foreign key constrains a squad. Later assessment
features can therefore pair one squad with multiple tactics without duplicating imports.
`SquadTacticApplication` records those explicit many-to-many pairings. It deliberately has
no arbitrary score until tactic positions, roles and instructions have typed parsers.

Each tactic may also own one current `ScreenshotDerivedTacticDefinition`. This is the
evidence layer produced by processing the tactic's current Formation, In Possession and Out
of Possession screenshots. Its normalized child tables retain phase-specific formation
slots, team instructions, validation issues, confidence, correction state and source-import
provenance. These persistence models remain separate from the framework-independent parser
models and Qt display models. The existing SQL table remains named
`structured_tactic_definitions` for database compatibility. Database initialization applies
this upgrade additively with SQLAlchemy metadata creation: missing screenshot-derived tactic
tables are created while existing tactics, imports, squads and players remain untouched.

FMSAT now also persists the football object model in a dedicated schema owned by
`TacticStore`. `object_model_tactics` stores one canonical saved tactic per normalized name,
while child tables retain in-possession and out-of-possession formations, ordered positions,
formation team instructions, position instructions, and transition instructions. This schema
is intentionally separate from `ScreenshotDerivedTacticDefinition`: screenshot-derived data
records what was observed, while the football object model is the usable model generated
from that evidence. Re-imported screenshot evidence requires the object model to be
regenerated before it represents the latest capture.
Object-model positions retain the evidence-bearing slot ID, duty, normalized coordinates,
confidence, source import and validation state alongside their canonical position and role.
The player visible in a Formation screenshot remains in the screenshot-derived evidence and
may support transient cross-phase linking, but is deliberately omitted from the reusable
tactic model; player mappings come only from explicit squad assignment. Extractors never
manufacture missing slots or instructions:
unsupported coverage is stored as unresolved issues until an observed extractor or user
review supplies it.

Formation processing now crops the configured In Possession and Out of Possession pitches,
detects coloured role tiles with computer vision, and applies OCR only to each detected tile.
The complete cropped Tactics Planner capture remains the Formation reference frame. A
geometry-selected profile handles both the compact two-pitch layout and the wider layout
with its squad table, avoiding accidental selection of an interior contour that truncates
the pitches.
Tile centres are normalized against their pitch crop and classified through configurable
pitch zones. Cross-phase identity uses displayed player, shirt number where retained,
relative ordering and spatial proximity; ambiguous and unmatched links remain explicit
issues. Instruction processing crops each configured card and persists a value only when OCR
and coloured selected-state evidence identify exactly one canonical selection. Missing,
unknown or ambiguous selections create issues instead of default instruction rows.
Selection scoring samples the complete option row rather than colour immediately
around OCR text. When several options contain coloured controls, one value is
accepted only if its row has a configured visual margin over the next candidate;
otherwise the category remains ambiguous. Non-canonical labels are excluded from
the comparison so card headings cannot become instruction values.

Regeneration applies an integrity gate before `TacticStore` is called. The extracted draft
must be complete and the generated formations must each contain eleven evidence-bearing,
resolved positions. An incomplete extraction retains its issues for review but cannot
replace the saved football object model. When a saved model is displayed, its own persisted
positions remain authoritative; newer partial extraction slots are not overlaid on its pitch.
The FM26 Tactics Planner Both view does not expose a separate duty. An absent duty therefore
remains `null`, is displayed as **Not shown**, and does not block an otherwise observed
position and role from entering the generated formation. A duty is retained whenever an
explicit source supplies it; the builder never creates a synthetic `Default` duty.

Tactic maintenance diagnostics are rendered with explicit opaque palettes. The
validation issue viewport owns its dark background and scrollbar styling, while the
progress dialog owns its panel, label, track and chunk colours. This avoids platform
palette leakage and prevents the tactic workspace showing through modal progress UI.
Blocking screenshot extraction executes in a single worker thread while a nested Qt
event loop services repaint and desktop heartbeat events. The caller still receives the
result synchronously before applying completeness checks or writing the object model.

New squads may also own `SquadClubScreenshot` records. The associated Club Information
screenshot supplies the squad-card badge image. It is previewed and persisted through
`ScreenshotStore` without screen detection, OCR or player parsing. Keeping this provenance
in SQLite avoids a second source of truth and lets squad deletion clean up the owned image.

The supported workflow captures Club Information, Formation, In Possession, Out of
Possession and Squad Attributes screens. Only the tactic and Squad Attributes captures are
processed by their relevant extraction workflows; Club Information is retained as a visual
asset. FMSAT intentionally reads screenshots only. It neither reads Football Manager save
files nor communicates with or modifies a running Football Manager process.
