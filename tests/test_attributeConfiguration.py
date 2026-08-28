from pathlib import Path

import yaml

from fmsat.core.config import AttributeConfigurationService


def testAttributeActivationDefaultsTrueAndPersistsToggle(tmp_path: Path) -> None:
    path = tmp_path / "attributes.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "attributes": {
                    "finishing": {"abbreviation": "Fin", "order": 1},
                    "long_shots": {
                        "abbreviation": "Lon",
                        "order": 2,
                        "active": False,
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    service = AttributeConfigurationService(path)

    initial = {attribute.name: attribute.active for attribute in service.definitionsLoad()}
    assert initial == {"finishing": True, "long_shots": False}

    updated = service.activeSet("long_shots", True)

    assert {attribute.name: attribute.active for attribute in updated} == {
        "finishing": True,
        "long_shots": True,
    }
    persisted = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert persisted["attributes"]["long_shots"]["active"] is True
