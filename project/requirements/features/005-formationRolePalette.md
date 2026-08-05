# 005 — Formation role palette and icons

## Status

Backlog

## Objective

Use a consistent six-band colour language whenever FMSAT displays or discusses
roles within a tactic. Align each colour with the corresponding horizontal row
in the formation display and provide a compact icon that makes the role
abbreviation recognisable without reproducing Football Manager's dropdown.

## Required behavior

1. Define one reusable palette for the six formation rows:
   goalkeeper, defence, defensive midfield, midfield, attacking midfield and
   striker.
2. Use the same row colour in formation displays, role discussions, tactic
   summaries and any later role-selection controls.
3. Map a role to its colour from the formation row in which it is being used;
   do not assume that a role abbreviation always belongs to one fixed row.
4. Render a simple role icon as a compact rounded rectangle containing the role
   abbreviation in clear light text.
5. Do not include a dropdown arrow or split-button divider in the icon.
6. Preserve the abbreviation exactly as displayed for the tactic, including
   examples such as BGK, CB, DLP, AWB, WM, IF, FR and CHF.
7. Keep foreground and background contrast sufficient for normal text and
   avoid relying on colour alone when conveying the role.
8. Centralize palette values and row-to-colour mapping so Qt views, generated
   reports and future visualizations cannot drift apart.
9. In a tactic-specific player view, show the player's assigned role icon in
   place of generic position text. For example, a centre-back assigned as a
   Ball-Playing Centre-Back displays a defence-coloured **BCB** icon rather than
   `D (C)`.
10. Retain the player's natural position data separately for eligibility,
    filtering and editing; replacing the visible position with a role icon must
    not overwrite the imported position.
11. When no tactic or assigned role provides context, show the natural position
    text rather than inventing a role.

## Palette

The supplied Football Manager reference establishes this order and colour
family:

| Formation row | Colour family | Indicative base colour |
| --- | --- | --- |
| Goalkeeper | Slate violet | `#4b4d70` |
| Defence | Teal | `#0d7775` |
| Defensive midfield | Green | `#117b49` |
| Midfield | Blue | `#174b85` |
| Attacking midfield | Purple | `#6d2089` |
| Striker | Magenta | `#981667` |

The implementation may apply a lighter border or hover shade from the same
colour family, but the row identity must remain visually stable.

## Acceptance criteria

1. Each of the six formation rows resolves to exactly one palette entry.
2. A role icon displays its abbreviation without a dropdown arrow.
3. The same role can take different row colours when placed on different
   formation rows.
4. Unknown or incomplete row data produces a neutral accessible icon rather
   than guessing a tactical row.
5. Palette mapping and icon rendering are covered by deterministic tests.
6. At least one formation or tactic-discussion view uses the shared component
   before this requirement is marked complete.
7. A tactic-specific player view displays the assigned role abbreviation and
   row colour while the player's imported position remains stored unchanged.
8. A player with no assigned tactical role continues to display their natural
   position clearly.

## Out of scope

- Reproducing Football Manager's dropdown control.
- Copying proprietary Football Manager artwork or role icons.
- Inferring player suitability from the role colour.
- Defining the tactical meaning of individual role abbreviations.

## Delivery notes

- Keep row identity separate from the role abbreviation in the data model.
- Keep the tactic-role assignment separate from the player's natural position;
  the same player may have different roles in different tactics.
- Prefer a small vector or code-rendered icon so it remains sharp at different
  display scales.
- Treat the listed hex values as the captured reference palette and adjust only
  where accessibility testing requires it.
