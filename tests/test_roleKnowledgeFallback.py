"""Regression coverage for semantic role-weight fallback compatibility."""

from pathlib import Path

import yaml

from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService


def _service(directory: Path) -> RoleKnowledgeService:
    return RoleKnowledgeService(
        directory,
        TacticVocabulary(),
        {"positioning", "anticipation"},
        {"halfBack": {"positioning": 5, "anticipation": 5}},
    )


def testRoleWeightsNormalizeLegacyAbbreviationToSemanticRole(tmp_path: Path) -> None:
    service = _service(tmp_path / "roles")

    assert service.weightsLoad("HB") == {"positioning": 5, "anticipation": 5}


def testEmptyPersistedWeightsDoNotOverridePackagedPolicy(tmp_path: Path) -> None:
    roles = tmp_path / "roles"
    requirements = tmp_path / "requirements"
    requirements.mkdir(parents=True)
    (requirements / "halfBack.yaml").write_text(
        yaml.safe_dump({"roleCode": "halfBack", "attributeWeights": {}}),
        encoding="utf-8",
    )
    service = _service(roles)

    assert service.weightsLoad("halfBack") == {"positioning": 5, "anticipation": 5}
