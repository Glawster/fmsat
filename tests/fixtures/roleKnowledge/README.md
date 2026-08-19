# 007B Role Knowledge Golden Fixtures

These YAML files define the expected persisted result of resolving semantic role knowledge during the final requirement 007B clean-room acceptance test.

Do not invent missing Football Manager evidence. A role remains:

```yaml
confirmationState: unresolved
evidence: null
expectedDefinition: null
expectedRequirements: null
```

until its role-profile screenshot has been reviewed and confirmed.

Once confirmed, replace the unresolved marker with:

```yaml
roleCode: <semanticRoleCode>
confirmationState: confirmed
evidence:
  expectedPosition: <canonical position>
  position: <captured/confirmed position>
  roleName: <confirmed FM role name>
  phase: inPossession | outOfPossession
  abbreviation: <confirmed abbreviation>
  description: <confirmed description or null>
  behaviours: []
  keyAttributes: []
  playerInstructions: []
  sourceImport: role-profile.png
  confidence: 1.0
expectedDefinition:
  # Exact YAML mapping expected from RoleKnowledgeService.definitionConfirm().
expectedRequirements:
  # Exact YAML mapping expected from RoleKnowledgeService.weightsConfirm().
```

`tests/test_roleKnowledgeAcceptance.py` drives the real Qt role-profile review dialog and compares both persisted YAML mappings with these golden values.

The normal test suite skips the exact comparison while a fixture is unresolved. For the final 007B completion gate run:

```bash
FMSAT_007B_FINAL=1 QT_QPA_PLATFORM=offscreen pytest \
  tests/test_cleanRoom007b.py \
  tests/test_roleKnowledgeAcceptance.py
```

That command intentionally fails if either known Unknown role is still unresolved, has no confirmed abbreviation, has no explicit assessment weights, or would still render as `Unknown` in the Roles workspace.
