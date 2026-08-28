"""Internal completeness checks for Generic Role Fit role assessment policy."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.roleKnowledge import RoleKnowledgeService
from fmsat.core.parser import TacticVocabulary


@dataclass(frozen=True, slots=True)
class RoleAssessmentIntegrityResult:
    """One reproducible completeness report for known role assessment policy."""

    knownRoles: int
    completeRoles: int
    issues: tuple[str, ...]

    @property
    def missingRoles(self) -> int:
        return self.knownRoles - self.completeRoles

    @property
    def complete(self) -> bool:
        return not self.issues

    def text(self) -> str:
        """Render a compact plain-text report for status and application logs."""

        lines = [
            "Role assessment integrity",
            f"Known roles: {self.knownRoles}",
            f"Complete assessment roles: {self.completeRoles}",
            f"Roles with issues: {self.missingRoles}",
        ]
        if self.issues:
            lines.append("")
            lines.extend(self.issues)
        else:
            lines.extend(("", "All known roles have complete assessment policy."))
        return "\n".join(lines)


def roleAssessmentIntegrityCheck(
    vocabulary: TacticVocabulary,
    knowledge: RoleKnowledgeService,
) -> RoleAssessmentIntegrityResult:
    """Compare every recognised/defined role with key attributes and assessment weights."""

    definitions = {item.roleCode: item for item in knowledge.definitionsList()}
    # The integrity catalogue deliberately uses the union rather than vocabulary alone.
    # Recognition-only roles discovered from FM evidence must not disappear from this check.
    knownCodes = set(vocabulary.roles) | set(definitions) | set(knowledge.defaultWeights)
    known = tuple(sorted(knownCodes, key=str.casefold))
    issues: list[str] = []
    incomplete: set[str] = set()

    for roleCode in known:
        vocabularyRole = vocabulary.roles.get(roleCode)
        storedDefinition = definitions.get(roleCode)
        roleIssues: list[str] = []
        weights = knowledge.weightsLoad(roleCode)
        definition = knowledge.definitionLoad(roleCode)

        if not weights:
            roleIssues.append("assessment weights MISSING")
        else:
            unknownWeighted = sorted(set(weights) - set(knowledge.attributeIds))
            if unknownWeighted:
                roleIssues.append("unknown weighted attributes: " + ", ".join(unknownWeighted))

        if storedDefinition is not None and isinstance(definition, dict):
            rawKeyAttributes = definition.get("keyAttributes", ())
            keyAttributes = tuple(
                str(value)
                for value in rawKeyAttributes
                if isinstance(rawKeyAttributes, (list, tuple)) and str(value).strip()
            )
            if not keyAttributes:
                roleIssues.append("confirmed key attributes MISSING")
            elif weights:
                unweightedKeys = sorted(set(keyAttributes) - set(weights))
                if unweightedKeys:
                    roleIssues.append(
                        "key attributes without weights: " + ", ".join(unweightedKeys)
                    )

        if roleIssues:
            incomplete.add(roleCode)
            abbreviation = "?"
            if vocabularyRole is not None and vocabularyRole.abbreviations:
                abbreviation = vocabularyRole.abbreviations[0]
            elif storedDefinition is not None and storedDefinition.abbreviations:
                abbreviation = storedDefinition.abbreviations[0]
            issues.append(f"{roleCode} ({abbreviation}): " + "; ".join(roleIssues))

    return RoleAssessmentIntegrityResult(
        knownRoles=len(known),
        completeRoles=len(known) - len(incomplete),
        issues=tuple(issues),
    )
