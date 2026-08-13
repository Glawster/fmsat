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

New squads may also own `SquadClubScreenshot` records. The associated Club Information
screenshot supplies the squad-card badge image. It is previewed and persisted through
`ScreenshotStore` without screen detection, OCR or player parsing. Keeping this provenance
in SQLite avoids a second source of truth and lets squad deletion clean up the owned image.

The supported workflow captures Club Information, Formation, In Possession, Out of
Possession and Squad Attributes screens. Only the tactic and Squad Attributes captures are
processed by their relevant extraction workflows; Club Information is retained as a visual
asset. FMSAT intentionally reads screenshots only. It neither reads Football Manager save
files nor communicates with or modifies a running Football Manager process.
