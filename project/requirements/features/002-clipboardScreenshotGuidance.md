# 002 — Clipboard screenshot guidance

## Status

Completed

## Objective

Make FMSAT's screenshot capture workflow explicit in the UI so the user knows
which Football Manager screen to capture and that FMSAT will collect the
screenshot from the clipboard.

## Required behavior

1. Before each capture, display the name of the Football Manager screen FMSAT
   needs.
2. Tell the user to open that screen and take a screenshot.
3. State clearly that FMSAT will collect the screenshot from the clipboard.
4. Keep the instructions visible until the user starts or cancels the capture.
5. If the clipboard does not contain a supported image, keep the user in the
   screenshot workflow and offer **Screenshot ready** or **Cancel** without
   opening an unrelated file picker.
6. Apply the guidance consistently to tactic and squad screenshot captures.
7. For a known tactic, let the user identify the screenshot being captured so a
   single Formation, In Possession or Out of Possession capture can be updated
   without repeating the other tactic screenshots.

## Example wording

```text
Open the Tactic Formation screen in Football Manager and take a screenshot.
FMSAT will collect the screenshot from your clipboard.
```

The screen name and any screen-specific preparation instructions should be
substituted for each requested capture.

## Acceptance criteria

1. Every screenshot prompt identifies the requested Football Manager screen.
2. Every prompt asks the user to take a screenshot and says that FMSAT will
   collect it from the clipboard.
3. A supported clipboard image continues directly into the import workflow.
4. A missing or unsupported clipboard image produces a clear explanation and
   lets the user retake the screenshot without restarting the import.
5. Cancelling either the prompt or file picker does not create a partial import.
6. UI tests cover clipboard success, clipboard fallback and cancellation.
7. A user can select a known tactic, choose one tactic screenshot type and
   replace only that capture.

## Completion evidence

Delivered in Phase 2. UI lifecycle tests cover clipboard acquisition, empty
clipboard guidance, retake, cancellation, preview and adaptive squad capture.
The complete FMSAT test suite, Ruff and `git diff --check` pass.

## Out of scope

- Taking screenshots automatically.
- Capturing or controlling Football Manager directly.
- Changing OCR or screen-detection behavior.
