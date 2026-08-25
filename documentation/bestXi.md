# Best XI Assignment

## Purpose

Best XI answers a different question from Generic Role Fit and Required Role Depth.

**Generic Role Fit asks:** Could this player's attributes suit this role?

**Best XI asks:** Of the players who can play this position, which set of unique players gives the strongest whole-team assignment that can reasonably be fielded now?

This boundary is intentional. A high Generic Role Fit outside a player's captured position family can identify an interesting retraining opportunity, but it is not sufficient evidence of current deployability. A later Potential XI or retraining-opportunity analysis can use that signal without allowing it to distort Best XI.

Required Role Depth asks which players are strongest for each tactic role/slot in isolation and which backups exist. Best XI asks which **set of unique players**, assigned across all simultaneous tactic slots, gives the strongest complete team from the available squad evidence.

This distinction matters because the player with the highest score for one slot may be more valuable in another slot. A slot-by-slot greedy selection can therefore produce a weaker or incomplete XI even when a better complete assignment exists.

Example:

- Lauren Hemp may be the strongest individual Second Striker candidate.
- Hemp may also be the only strong/available AML candidate.
- Laura Freigang may be a slightly weaker Second Striker candidate.
- Selecting Hemp at Second Striker first can leave AML uncovered.
- Selecting Freigang at Second Striker and Hemp at AML can cover both positions and produce the stronger whole XI.

Best XI must evaluate those assignments globally rather than treating each slot independently.

## Evidence used

Best XI does not invent a new player rating.

For each simultaneous tactic slot it reuses the existing Generic Role Fit evidence already calculated for the role required in each phase.

Where a slot has both In Possession and Out Of Possession roles, the current slot score is the arithmetic mean of the available phase-role Generic Role Fit scores. This is the same transparent `phaseMean` policy used by the existing role-depth calculation.

A player is a Best XI candidate for a slot only when:

- all required phase roles for that slot have calculable Generic Role Fit evidence; and
- the player's captured positions include the slot's position family.

Players outside the slot's position family do not compete for that Best XI slot, regardless of their Generic Role Fit score. Missing or unmappable positional evidence is not treated as familiarity. Missing role policy, missing player attributes, unresolved semantic role identity, or other unavailable evidence also remains unavailable rather than being guessed.

`Training required` remains useful in role-depth, player analysis and future retraining-opportunity views. It is not a normal Best XI selection state because those players are excluded during candidate eligibility.

## Optimisation objective

The optimiser uses a strict lexicographic objective. Earlier priorities always outrank later priorities.

1. **Maximise covered simultaneous tactic slots.** A complete XI beats an incomplete XI, provided the additional assignments have calculable role-fit evidence and position-family familiarity.
2. **Enforce player uniqueness.** One player can fill at most one simultaneous tactic slot.
3. **Maximise total slot Generic Role Fit.** Among assignments covering the same number of slots, choose the highest summed slot score.
4. **Maximise the weakest selected slot fit.** When total score is equal, prefer the more balanced XI rather than one containing an unnecessarily weak assignment.
5. **Use a deterministic identity tie-break.** If all football/evidence objectives are equal, alphabetical player identity provides a stable result so the same evidence always produces the same XI.

The optimiser therefore does not use tactic-slot order as a selection priority.

## Algorithm

FMSAT models the problem as a constrained assignment over the simultaneous tactic slots.

For each slot it first restricts candidates to players whose captured positions cover the slot's position family. Among those players, it retains candidates with complete phase-role evidence and calculates each player's slot score. It then processes the available players while maintaining the best known assignment for each bit-mask of covered slots.

Because a processed player is considered only once, each state automatically respects the one-player/one-slot constraint. For each coverage mask, only the state with the strongest objective tuple is retained. With eleven tactic slots this state space is small (`2^11` coverage masks) and avoids a naive permutation search across the whole squad.

After all players have been considered, FMSAT selects the state with the greatest number of covered slots and then applies the remaining objective priorities in order.

## Transparency

Best XI retains evidence for each selected assignment.

The selected-player tooltip records:

- how many simultaneous slots the global XI covers;
- the total slot-fit score for the selected XI;
- the weakest selected slot score;
- the selected player's IP/OOP role-fit inputs and resulting slot score;
- whether captured positional evidence covers the slot family;
- when relevant, that a locally higher-scoring player was assigned elsewhere because doing so produced the stronger global XI.

This allows a selection such as `Freigang at SS / Hemp at AML` to be explained rather than appearing to contradict the role-depth rankings.

## Boundaries

Best XI currently uses Generic Role Fit to rank eligible assignments and captured positional evidence to decide eligibility.

It does **not** yet include:

- tactical interaction or partnership scoring;
- player traits as tactical-fit modifiers;
- form, morale, condition, fatigue, injuries, suspensions or match sharpness;
- opposition-specific selection;
- recruitment recommendations;
- rotation or alternative-XI generation.

Those concerns must be introduced explicitly in later increments rather than being hidden inside the Generic Role Fit assignment policy.
