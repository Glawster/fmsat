# Squad screenshot regression fixtures

Squad screenshots are canonical OCR evidence. Each named directory represents one reviewed squad fixture and must be paired with a manually reviewed YAML file under `tests/fixtures/squads/`.

Current fixture:

```text
tests/screenshots/squads/bristolWomen/
├── squad1.png
├── squad2.png
├── squad3.png
├── squad4.png
└── goalkeeper.png

tests/fixtures/squads/bristolWomen.yaml
```

The Bristol Women fixture contains 38 distinct players. `squad1.png` and `squad2.png` cover the Default 1 attribute view; `squad3.png` and `squad4.png` cover Default 2; `goalkeeper.png` contains all four goalkeepers and goalkeeper-specific attributes.

Expected YAML is reviewed from the visible Football Manager screenshots. It must never be generated from FMSAT OCR output, because that would make the code under test its own oracle.

Two visible FM columns are deliberately not modelled by the current FMSAT attribute configuration:

- `Long Shots` in Default 1
- `Bravery` in Default 2

They remain recorded as visible ignored columns in the golden YAML so their presence and Natural Fitness geometry are explicit.

Normal pytest runs validate fixture structure and configured-attribute coverage while skipping expensive real OCR. Run the full golden OCR acceptance with:

```bash
FMSAT_OCR_FIXTURES=1 QT_QPA_PLATFORM=offscreen pytest tests/test_squadScreenshotFixtures.py
```

A mismatch must be reviewed against the screenshot. Correct the parser/OCR when the fixture is right; correct the YAML only when manual review shows the golden transcription itself is wrong.
