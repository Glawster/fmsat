# Source prompt — requirement 009

Create req 9 tactic management, this will follow

## 1. Overview

This is the landing page.

Show the tactic name, created date, formation, mentality, squads using it,
status and last-analysed date alongside the formation diagram reconstructed by
FMSAT. Use a clean vector-style pitch rather than the screenshot itself.

## 2. Shape

Capture In Possession and Out of Possession shape from the formation screenshots.
For every position retain pitch coordinates, position, role, duty and an optional
assigned player. This must allow FMSAT to redraw and compare formations, analyse
spacing and later calculate role suitability without reopening screenshots.

## 3. Team Instructions

Capture every visible instruction individually under a meaningful name, never as
an opaque numbered flag. Group them into Build Up, Attack, Transition and Defence.
Never infer an instruction.

## 4. Analysis

Initially this tab will be mostly empty. Later it can show a generated system
summary, style labels, aggression, risk and player-role needs. This information
is generated, not imported.

Capture all visible metadata, both formations, coordinates, roles, duties,
instructions and mentality. Set pieces, opposition instructions and individual
instructions can follow later.

Squad assignment should not use OCR. Model it as tactic, assigned squad and
player mapping.

The tactic screen should provide Overview, Shape, Instructions and Analysis tabs.
Screenshots are evidence used by OCR and parsing to produce a structured tactic
model; they are not the primary representation.

Add version history. Importing a modified tactic should create a new revision
rather than overwrite the previous one. Users should later be able to see what
changed between versions and relate versions to results when result evidence is
available.
