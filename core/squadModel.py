"""Editable squad object-model generation, loading, and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fmsat.core.config import AttributeDefinition, Configuration
from fmsat.core.images import ImagePreprocessor, PreprocessingOptions, imageLoad
from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import SquadAttributesParser
from fmsat.core.services import ImportResult, squadCapturesMerge
from fmsat.core.detection import ScreenType
from fmsat.database.models import (
    ImportSession,
    ObjectModelPlayer,
    ObjectModelPlayerAttribute,
    ObjectModelPlayerTrait,
    ObjectModelSquad,
    Player,
    Squad,
    SquadScreenshot,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload

logger = getLogger()


@dataclass(frozen=True, slots=True)
class SquadModelPlayer:
    """One editable player detached from SQLAlchemy persistence."""

    name: str
    positions: str
    ca: str
    pa: str
    confidence: float | None
    attributes: tuple[tuple[str, int | None], ...]
    sourceImportSessionId: int | None = None
    validationState: str = "extracted"
    traits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SquadModel:
    """Current editable squad facts used by assessment and presentation."""

    name: str
    players: tuple[SquadModelPlayer, ...]
    generatedAt: datetime
    updatedAt: datetime
    evidenceSuperseded: bool
    regenerationRequired: bool = False


class SquadModelService:
    """Keep screenshot evidence separate from the editable current squad model."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    ## model

    def modelLoad(self, squadName: str, *, create: bool = True) -> SquadModel | None:
        """Load a squad model, optionally generating its first model from OCR evidence."""

        cleanName = squadName.strip()
        if not cleanName:
            return None
        with Session(self.engine) as session:
            stored = self._storedLoad(session, cleanName)
            if stored is not None:
                return self._modelDetach(stored)
        if not create:
            return None
        return self._modelGenerate(cleanName)

    def modelSave(self, model: SquadModel) -> SquadModel:
        """Persist edits, or explicitly regenerate a model marked as stale."""

        cleanName = model.name.strip()
        if not cleanName:
            raise ValueError("Squad name is required")
        if model.regenerationRequired:
            logger.doing(f"regenerating squad model {cleanName}")
            return self._modelRegenerate(cleanName)
        now = datetime.now()
        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == cleanName.casefold())
                .options(selectinload(Squad.screenshots))
            )
            stored = self._storedLoad(session, cleanName)
            if stored is None:
                stored = ObjectModelSquad(
                    name=cleanName,
                    normalizedName=cleanName.casefold(),
                    sourceSquad=source,
                    generatedAt=model.generatedAt,
                )
                session.add(stored)
            else:
                stored.players.clear()
                session.flush()
            stored.name = cleanName
            stored.sourceSquad = source
            stored.updatedAt = now
            stored.players.extend(
                self._playerStore(player, manual=True) for player in model.players
            )

            if source is not None:
                for capture in source.screenshots:
                    capture.supersededAt = now
            session.flush()
            result = self._modelDetach(stored)
        return result

    ## generation

    def _modelGenerate(self, squadName: str) -> SquadModel | None:
        """Create the first editable model from all available OCR evidence."""

        now = datetime.now()
        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(
                    selectinload(Squad.screenshots)
                    .selectinload(SquadScreenshot.importSession)
                    .selectinload(ImportSession.players)
                    .selectinload(Player.attributes)
                )
            )
            if source is None:
                return None

            stored = ObjectModelSquad(
                name=source.name,
                normalizedName=source.normalizedName,
                sourceSquad=source,
                generatedAt=now,
                updatedAt=now,
            )
            for _, evidenceRows in self._playerEvidenceGroups(source):
                stored.players.append(self._playerFromEvidenceRows(evidenceRows))
            session.add(stored)
            session.flush()
            return self._modelDetach(stored)

    def _modelRegenerate(self, squadName: str) -> SquadModel:
        """Re-OCR saved screenshots, replacing derived facts while retaining manual traits."""

        now = datetime.now()
        logger.info("squad regeneration loading saved screenshot evidence: %s", squadName)
        with Session(self.engine) as session:
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(
                    selectinload(Squad.screenshots).selectinload(
                        SquadScreenshot.importSession
                    )
                )
            )
            if source is None:
                raise ValueError(f"Squad evidence does not exist: {squadName}")
            captures = tuple(
                sorted(source.screenshots, key=lambda item: item.importSessionId)
            )
            filenames = tuple(capture.importSession.imageFilename for capture in captures)
            sourceImportSessionId = max(
                (capture.importSessionId for capture in captures),
                default=None,
            )
        if not filenames:
            raise ValueError(f"No saved squad screenshots exist for {squadName}")

        logger.value("squad regeneration screenshots", len(filenames))
        parser, preprocessor = self._regenerationParserCreate()
        merged: ImportResult | None = None
        for index, filename in enumerate(filenames, start=1):
            logger.info(
                "squad regeneration OCR %d/%d: %s",
                index,
                len(filenames),
                filename,
            )
            processed = preprocessor.process(imageLoad(filename))
            players = parser.parse(processed)
            if not players:
                raise ValueError(f"No player rows could be regenerated from {filename}")
            result = ImportResult(
                source=filename,
                screenType=ScreenType.SQUAD_ATTRIBUTES,
                players=players,
            )
            merged = result if merged is None else squadCapturesMerge(merged, result)
        if merged is None or not merged.players:
            raise ValueError("Squad regeneration produced no player data")
        logger.value("squad regeneration rebuilt players", len(merged.players))
        if merged.mergeConflicts:
            logger.warning(
                "squad regeneration found %d complementary-view conflicts",
                len(merged.mergeConflicts),
            )

        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(selectinload(Squad.screenshots))
            )
            stored = self._storedLoad(session, squadName)
            if source is None or stored is None:
                raise ValueError(f"Squad model does not exist: {squadName}")
            traitsByPlayer = {
                player.normalizedName: tuple(
                    trait.traitName
                    for trait in sorted(player.traits, key=lambda item: item.traitName.casefold())
                )
                for player in stored.players
            }
            stored.players.clear()
            session.flush()
            stored.name = source.name
            stored.normalizedName = source.normalizedName
            stored.sourceSquad = source
            stored.generatedAt = now
            stored.updatedAt = now
            for extracted in merged.players:
                normalizedName = extracted.name.strip().casefold()
                stored.players.append(
                    ObjectModelPlayer(
                        name=extracted.name.strip(),
                        normalizedName=normalizedName,
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                        sourceImportSessionId=sourceImportSessionId,
                        validationState="extracted",
                        attributes=[
                            ObjectModelPlayerAttribute(
                                attributeName=name,
                                attributeValue=value,
                                validationState="extracted",
                            )
                            for name, value in sorted(extracted.attributes.items())
                        ],
                        traits=[
                            ObjectModelPlayerTrait(
                                traitName=trait,
                                validationState="corrected",
                            )
                            for trait in traitsByPlayer.get(normalizedName, ())
                        ],
                    )
                )
            for capture in source.screenshots:
                capture.supersededAt = now
            session.flush()
            result = self._modelDetach(stored)

        logger.value("squad regeneration still required", result.regenerationRequired)
        if result.regenerationRequired:
            raise ValueError(
                "Squad regeneration completed but newer player evidence remains unconsumed"
            )
        logger.done(f"squad model regeneration finished for {squadName}")
        return result

    @staticmethod
    def _regenerationParserCreate() -> tuple[SquadAttributesParser, ImagePreprocessor]:
        """Build the current production squad parser for retained screenshot evidence."""

        config = Configuration()
        ocr = PaddleOcrEngine()
        parserAttributes = tuple(
            AttributeDefinition(
                definition.name,
                definition.name,
                definition.order,
            )
            for definition in config.attributes
        )
        parser = SquadAttributesParser(ocr, config.regions, parserAttributes)
        preprocessor = ImagePreprocessor(
            PreprocessingOptions.fromMapping(config.screens.get("preprocessing", {}))
        )
        return parser, preprocessor

    @staticmethod
    def _playerEvidenceGroups(
        source: Squad,
    ) -> tuple[tuple[str, tuple[Player, ...]], ...]:
        """Group every OCR row per player, newest first, so views can complement each other."""

        grouped: dict[str, list[Player]] = {}
        for capture in sorted(
            source.screenshots,
            key=lambda item: (item.importSession.date, item.importSession.id),
            reverse=True,
        ):
            for player in sorted(
                capture.importSession.players,
                key=lambda item: item.id,
                reverse=True,
            ):
                normalizedName = player.name.strip().casefold()
                grouped.setdefault(normalizedName, []).append(player)
        return tuple((name, tuple(grouped[name])) for name in sorted(grouped))

    @staticmethod
    def _playerFromEvidenceRows(
        players: tuple[Player, ...],
        *,
        traits: tuple[str, ...] = (),
    ) -> ObjectModelPlayer:
        """Merge complementary screenshot rows, preferring newest observed values."""

        if not players:
            raise ValueError("At least one player evidence row is required")
        newest = players[0]

        def newestText(field: str) -> str:
            return next(
                (
                    str(value).strip()
                    for player in players
                    if (value := getattr(player, field, None)) is not None
                    and str(value).strip()
                ),
                "",
            )

        attributes: dict[str, int | None] = {}
        for player in players:
            for attribute in sorted(player.attributes, key=lambda item: item.attributeName):
                current = attributes.get(attribute.attributeName)
                if attribute.attributeName not in attributes or current is None:
                    attributes[attribute.attributeName] = attribute.attributeValue

        confidence = next(
            (player.confidence for player in players if player.confidence is not None),
            None,
        )
        sourceImportSessionId = max(
            (player.importSessionId for player in players if player.importSessionId is not None),
            default=None,
        )
        return ObjectModelPlayer(
            name=newest.name,
            normalizedName=newest.name.strip().casefold(),
            positions=newestText("positions"),
            ca=newestText("ca"),
            pa=newestText("pa"),
            confidence=confidence,
            sourceImportSessionId=sourceImportSessionId,
            validationState="extracted",
            attributes=[
                ObjectModelPlayerAttribute(
                    attributeName=name,
                    attributeValue=value,
                    validationState="extracted",
                )
                for name, value in sorted(attributes.items())
            ],
            traits=[
                ObjectModelPlayerTrait(traitName=name, validationState="corrected")
                for name in traits
            ],
        )

    ## persistence mapping

    @staticmethod
    def _modelDetach(stored: ObjectModelSquad) -> SquadModel:
        """Copy one eager-loaded row graph into framework-independent values."""

        sourceImportIds = (
            [
                capture.importSessionId
                for capture in stored.sourceSquad.screenshots
                if capture.supersededAt is None and capture.importSession.players
            ]
            if stored.sourceSquad is not None
            else []
        )
        modelImportIds = [
            player.sourceImportSessionId
            for player in stored.players
            if player.sourceImportSessionId is not None
        ]
        return SquadModel(
            name=stored.name,
            players=tuple(
                SquadModelPlayer(
                    name=player.name,
                    positions=player.positions,
                    ca=player.ca,
                    pa=player.pa,
                    confidence=player.confidence,
                    sourceImportSessionId=player.sourceImportSessionId,
                    validationState=player.validationState,
                    attributes=tuple(
                        (attribute.attributeName, attribute.attributeValue)
                        for attribute in sorted(player.attributes, key=lambda item: item.attributeName)
                    ),
                    traits=tuple(
                        trait.traitName
                        for trait in sorted(player.traits, key=lambda item: item.traitName.casefold())
                    ),
                )
                for player in sorted(stored.players, key=lambda item: item.name.casefold())
            ),
            generatedAt=stored.generatedAt,
            updatedAt=stored.updatedAt,
            evidenceSuperseded=bool(
                stored.sourceSquad
                and stored.sourceSquad.screenshots
                and all(capture.supersededAt is not None for capture in stored.sourceSquad.screenshots)
            ),
            regenerationRequired=bool(
                sourceImportIds
                and (not modelImportIds or max(sourceImportIds) > max(modelImportIds))
            ),
        )

    @staticmethod
    def _playerStore(player: SquadModelPlayer, *, manual: bool) -> ObjectModelPlayer:
        """Map one detached player into editable object-model persistence."""

        state = "corrected" if manual else player.validationState
        return ObjectModelPlayer(
            name=player.name.strip(),
            normalizedName=player.name.strip().casefold(),
            positions=player.positions.strip(),
            ca=player.ca.strip(),
            pa=player.pa.strip(),
            confidence=player.confidence,
            sourceImportSessionId=player.sourceImportSessionId,
            validationState=state,
            attributes=[
                ObjectModelPlayerAttribute(
                    attributeName=name,
                    attributeValue=value,
                    validationState=state,
                )
                for name, value in sorted(player.attributes)
            ],
            traits=[
                ObjectModelPlayerTrait(traitName=name, validationState=state)
                for name in sorted(
                    {trait.strip() for trait in player.traits if trait.strip()},
                    key=str.casefold,
                )
            ],
        )

    @staticmethod
    def _storedLoad(session: Session, squadName: str) -> ObjectModelSquad | None:
        """Load one complete squad-model row graph inside the caller's session."""

        return session.scalar(
            select(ObjectModelSquad)
            .where(ObjectModelSquad.normalizedName == squadName.casefold())
            .options(
                selectinload(ObjectModelSquad.sourceSquad)
                .selectinload(Squad.screenshots)
                .selectinload(SquadScreenshot.importSession)
                .selectinload(ImportSession.players),
                selectinload(ObjectModelSquad.players).selectinload(ObjectModelPlayer.attributes),
                selectinload(ObjectModelSquad.players).selectinload(ObjectModelPlayer.traits),
            )
        )
