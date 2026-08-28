"""Regression tests for the internal role-assessment completeness check."""

from types import SimpleNamespace

from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleAssessmentIntegrity import roleAssessmentIntegrityCheck


def _knowledge(weights, definitions=()):
    definitionsByCode = {item.roleCode: item for item in definitions}
    return SimpleNamespace(
        attributeIds=frozenset({"pace"}),
        defaultWeights=weights,
        definitionsList=lambda: definitions,
        definitionLoad=lambda roleCode: (
            {"keyAttributes": ["pace"]} if roleCode in definitionsByCode else None
        ),
        weightsLoad=lambda roleCode: dict(weights.get(roleCode, {})),
    )


def testIntegrityReportIdentifiesKnownRoleWithoutWeights() -> None:
    vocabulary = TacticVocabulary()
    missingRole = next(iter(vocabulary.roles))
    weights = {roleCode: {"pace": 5} for roleCode in vocabulary.roles if roleCode != missingRole}

    result = roleAssessmentIntegrityCheck(vocabulary, _knowledge(weights))

    assert result.knownRoles == len(vocabulary.roles)
    assert result.completeRoles == len(vocabulary.roles) - 1
    assert any(
        issue.startswith(missingRole) and "assessment weights MISSING" in issue
        for issue in result.issues
    )


def testIntegrityReportIncludesRecognitionOnlyDefinitions() -> None:
    vocabulary = TacticVocabulary()
    definition = SimpleNamespace(roleCode="futureObservedRole", abbreviations=("FOR",))
    weights = {roleCode: {"pace": 5} for roleCode in vocabulary.roles}

    result = roleAssessmentIntegrityCheck(vocabulary, _knowledge(weights, (definition,)))

    assert result.knownRoles == len(vocabulary.roles) + 1
    assert result.completeRoles == len(vocabulary.roles)
    assert "futureObservedRole (FOR): assessment weights MISSING" in result.issues


def testIntegrityReportRendersPlainText() -> None:
    vocabulary = TacticVocabulary()
    weights = {roleCode: {"pace": 5} for roleCode in vocabulary.roles}

    rendered = roleAssessmentIntegrityCheck(vocabulary, _knowledge(weights)).text()

    assert rendered.startswith("Role assessment integrity\n")
    assert f"Known roles: {len(vocabulary.roles)}" in rendered
    assert "All known roles have complete assessment policy." in rendered
    assert "┌" not in rendered
    assert "│" not in rendered
    assert "└" not in rendered
