# Development Status

Last updated: 2026-08-10

Current Branch

    fmsat/phase3

Current Phase

    Phase 3 – Structured Tactical Knowledge

---

## Completed Requirements

| ID | Requirement | Status |
|----|-------------|--------|
|002|Clipboard screenshots|Complete|
|008|Welcome screen|Complete|

---

## Active Requirements

### Requirement 006

Status

In Progress

Completed

- Tactical vocabulary
- Tactical domain model
- Role profile parser
- Role knowledge gaps
- Role profile review dialog

Remaining

- Structured tactic persistence
- Review UI
- CLI diagnostics

Delivered extraction components

- Computer-vision Formation tile detection with focused OCR
- Configurable pitch-zone position normalization
- Evidence-ranked cross-phase slot linking
- Selected-only team-instruction parsing
- Explicit unresolved issues for missing and ambiguous evidence

The normalized regions in `config/tacticExtraction.yaml` are the initial FM26 profile and
must be verified against retained full-resolution captures. New skins or layouts should add
calibrated configuration rather than parser constants.

---

### Requirement 010

Status

In Progress

Completed

- Role profile parser
- User role knowledge
- Knowledge validation
- YAML persistence

Remaining

- Position definitions
- Attribute master list
- Assessment requirements
- Tactical modifiers
- Scoring
- Knowledge versioning

---

## Upcoming Requirement

007 – Role-centric Squad Assessment

Blocked until:

- Requirement 006 complete
- Requirement 010 factual knowledge complete

---

## Technical Debt

Low priority

- Remove generated egg-info from repository
- Move parser modules into dedicated package
- Split MainWindow into workflow controllers
