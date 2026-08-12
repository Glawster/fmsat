"""Transactional database gateway."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from fmsat.core.logUtils import getLogger
from sqlalchemy import create_engine as createEngine
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.validation import PlayerValidator

from .models import (
    AttributeSnapshot,
    Base,
    ImportSession,
    ObjectModelTactic,
    Player,
    Squad,
    SquadClubScreenshot,
    SquadScreenshot,
    SquadTacticApplication,
    Tactic,
    TacticScreenshot,
)
from .records import (
    DeletionRecord,
    SquadCleanupRecord,
    SquadPlayerRecord,
    SquadRecord,
    TacticDetailRecord,
    TacticRecord,
)

logger = getLogger()


class DatabaseError(RuntimeError):
    """Raised when a database operation cannot be completed."""


class Database:
    """Owns SQLite initialization and atomic import persistence."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = createEngine(f"sqlite:///{path}", future=True)
            self._sessionFactory = sessionmaker(self.engine, expire_on_commit=False)
        except (OSError, SQLAlchemyError) as exc:
            raise DatabaseError(f"Unable to initialize database: {exc}") from exc

    def initialize(self) -> None:
        """Add missing schema tables without replacing existing user data."""

        try:
            Base.metadata.create_all(self.engine)
            logger.info("database initialized path=%s", self.path)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to create database tables: {exc}") from exc

    def importSave(
        self,
        imageFilename: str,
        screenType: ScreenType,
        extractedPlayers: list[ExtractedPlayer],
        tacticName: str,
    ) -> ImportSession:
        """Persist a legacy tactic-linked squad import.

        New callers should use ``squadImportSave`` so squads remain independent
        from tactics.
        """

        try:
            with self._sessionFactory.begin() as session:
                cleanName = tacticName.strip()
                if not cleanName:
                    raise DatabaseError("A tactic name is required")
                normalizedName = cleanName.casefold()
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == normalizedName)
                )
                if tactic is None:
                    tactic = Tactic(name=cleanName, normalizedName=normalizedName)
                    session.add(tactic)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=screenType.value,
                )
                session.add(importSession)
                importSession.tacticCapture = TacticScreenshot(
                    tactic=tactic,
                    screenType=screenType.value,
                )
                for extracted in extractedPlayers:
                    player = Player(
                        name=extracted.name.strip(),
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                    )
                    player.attributes.extend(
                        AttributeSnapshot(attributeName=name, attributeValue=value)
                        for name, value in extracted.attributes.items()
                    )
                    importSession.players.append(player)
            logger.info(
                "Saved import session %s with %d players",
                importSession.id,
                len(extractedPlayers),
            )
            return importSession
        except SQLAlchemyError as exc:
            logger.exception("Database write failed")
            raise DatabaseError(f"Unable to save import: {exc}") from exc

    def tacticImportSave(
        self,
        imageFilename: str,
        screenType: ScreenType,
        tacticName: str,
    ) -> ImportSession:
        """Persist one confirmed tactic screenshot."""

        tacticTypes = {
            ScreenType.TACTIC_FORMATION,
            ScreenType.TACTIC_IN_POSSESSION,
            ScreenType.TACTIC_OUT_OF_POSSESSION,
        }
        if screenType not in tacticTypes:
            raise DatabaseError(f"Not a tactic screenshot type: {screenType.value}")
        try:
            with self._sessionFactory.begin() as session:
                cleanName = tacticName.strip()
                if not cleanName:
                    raise DatabaseError("A tactic name is required")
                normalizedName = cleanName.casefold()
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == normalizedName)
                )
                if tactic is None:
                    tactic = Tactic(name=cleanName, normalizedName=normalizedName)
                    session.add(tactic)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=screenType.value,
                )
                importSession.tacticCapture = TacticScreenshot(
                    tactic=tactic,
                    screenType=screenType.value,
                )
                session.add(importSession)
            logger.action(
                "tactic import saved tactic=%r screenType=%s importSession=%s image=%s",
                cleanName,
                screenType.value,
                importSession.id,
                imageFilename,
            )
            return importSession
        except SQLAlchemyError as exc:
            logger.exception("tactic import database write failed")
            raise DatabaseError(f"Unable to save tactic import: {exc}") from exc

    def squadImportSave(
        self,
        imageFilename: str,
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Persist a confirmed squad import independently of any tactic."""

        try:
            with self._sessionFactory.begin() as session:
                cleanName = squadName.strip()
                if not cleanName:
                    raise DatabaseError("A squad name is required")
                normalizedName = cleanName.casefold()
                squad = session.scalar(select(Squad).where(Squad.normalizedName == normalizedName))
                if squad is None:
                    squad = Squad(name=cleanName, normalizedName=normalizedName)
                    session.add(squad)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=ScreenType.SQUAD_ATTRIBUTES.value,
                )
                importSession.squadCapture = SquadScreenshot(squad=squad)
                for extracted in extractedPlayers:
                    player = Player(
                        name=extracted.name.strip(),
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                    )
                    player.attributes.extend(
                        AttributeSnapshot(attributeName=name, attributeValue=value)
                        for name, value in extracted.attributes.items()
                    )
                    importSession.players.append(player)
                session.add(importSession)
            logger.action(
                "squad import saved squad=%r players=%d importSession=%s image=%s",
                cleanName,
                len(extractedPlayers),
                importSession.id,
                imageFilename,
            )
            return importSession
        except SQLAlchemyError as exc:
            logger.exception("squad import database write failed")
            raise DatabaseError(f"Unable to save squad import: {exc}") from exc

    def squadClubImageSave(self, imageFilename: str, squadName: str) -> ImportSession:
        """Persist a Club Information screenshot for a new or existing squad."""

        try:
            with self._sessionFactory.begin() as session:
                cleanName = squadName.strip()
                if not cleanName:
                    raise DatabaseError("A squad name is required")
                normalizedName = cleanName.casefold()
                squad = session.scalar(select(Squad).where(Squad.normalizedName == normalizedName))
                if squad is None:
                    squad = Squad(name=cleanName, normalizedName=normalizedName)
                    session.add(squad)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=ScreenType.CLUB_INFORMATION.value,
                )
                importSession.clubCapture = SquadClubScreenshot(squad=squad)
                session.add(importSession)
            logger.action("squad club image saved squad=%r image=%s", cleanName, imageFilename)
            return importSession
        except SQLAlchemyError as exc:
            logger.exception("squad club image database write failed")
            raise DatabaseError(f"Unable to save squad club image: {exc}") from exc

    def squadImportPairSave(
        self,
        imageFilenames: list[str],
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Compatibility wrapper for a two-image squad capture batch."""

        if len(imageFilenames) != 2:
            raise DatabaseError("A paired squad import requires exactly two screenshots")
        return self.squadImportBatchSave(imageFilenames, extractedPlayers, squadName)

    def squadImportBatchSave(
        self,
        imageFilenames: list[str],
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Persist all capture pages and one merged squad player snapshot."""

        if not imageFilenames:
            raise DatabaseError("A squad capture batch requires at least one screenshot")
        try:
            with self._sessionFactory.begin() as session:
                cleanName = squadName.strip()
                if not cleanName:
                    raise DatabaseError("A squad name is required")
                normalizedName = cleanName.casefold()
                squad = session.scalar(select(Squad).where(Squad.normalizedName == normalizedName))
                if squad is None:
                    squad = Squad(name=cleanName, normalizedName=normalizedName)
                    session.add(squad)
                importSessions = [
                    ImportSession(
                        imageFilename=filename,
                        screenType=ScreenType.SQUAD_ATTRIBUTES.value,
                        squadCapture=SquadScreenshot(squad=squad),
                    )
                    for filename in imageFilenames
                ]
                for extracted in extractedPlayers:
                    player = Player(
                        name=extracted.name.strip(),
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                    )
                    player.attributes.extend(
                        AttributeSnapshot(attributeName=name, attributeValue=value)
                        for name, value in extracted.attributes.items()
                    )
                    importSessions[0].players.append(player)
                session.add_all(importSessions)
            logger.action(
                "squad capture batch saved squad=%r players=%d captures=%d "
                "primaryImportSession=%s",
                cleanName,
                len(extractedPlayers),
                len(imageFilenames),
                importSessions[0].id,
            )
            return importSessions[0]
        except SQLAlchemyError as exc:
            logger.exception("squad capture batch database write failed")
            raise DatabaseError(f"Unable to save squad capture batch: {exc}") from exc

    def screenTypesForTactic(self, tacticName: str) -> set[ScreenType]:
        """Return screen types previously confirmed for a tactic."""

        normalizedName = tacticName.strip().casefold()
        try:
            with Session(self.engine) as session:
                values = session.scalars(
                    select(TacticScreenshot.screenType)
                    .join(Tactic)
                    .where(Tactic.normalizedName == normalizedName)
                ).all()
            return {ScreenType(value) for value in values if value in ScreenType._value2member_map_}
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to inspect tactic screenshots: {exc}") from exc

    def tacticsList(self) -> list[str]:
        """Return recognised tactic names alphabetically."""

        try:
            with Session(self.engine) as session:
                return list(session.scalars(select(Tactic.name).order_by(Tactic.name)).all())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list tactics: {exc}") from exc

    def tacticRecords(self) -> list[TacticRecord]:
        """Return tactic summaries, preferring saved object-model tactic names."""

        try:
            with Session(self.engine) as session:
                tactics = session.scalars(
                    select(Tactic)
                    .options(
                        selectinload(Tactic.objectModelTactic),
                        selectinload(Tactic.structuredDefinition),
                        selectinload(Tactic.screenshots).selectinload(
                            TacticScreenshot.importSession
                        ),
                    )
                    .order_by(Tactic.name)
                ).all()
                objectModels = session.scalars(
                    select(ObjectModelTactic)
                    .options(
                        selectinload(ObjectModelTactic.sourceTactic)
                        .selectinload(Tactic.screenshots)
                        .selectinload(TacticScreenshot.importSession)
                    )
                    .order_by(ObjectModelTactic.name)
                ).all()
                records = []
                # Saved object-model tactics are the canonical summaries when
                # they exist, but screenshot provenance still comes from the
                # linked source tactic import history.
                for model in objectModels:
                    source = model.sourceTactic
                    screenshots = source.screenshots if source is not None else []
                    formations = [
                        screenshot.importSession
                        for screenshot in screenshots
                        if screenshot.screenType == ScreenType.TACTIC_FORMATION.value
                    ]
                    latest = (
                        max(formations, key=lambda item: (item.date, item.id))
                        if formations
                        else None
                    )
                    records.append(
                        TacticRecord(
                            model.name,
                            len(screenshots),
                            latest.imageFilename if latest else None,
                            hasStructuredData=(
                                source.structuredDefinition is not None
                                if source is not None
                                else False
                            ),
                            hasObjectModelData=True,
                        )
                    )

                for tactic in tactics:
                    if tactic.objectModelTactic is not None:
                        continue
                    formations = [
                        screenshot.importSession
                        for screenshot in tactic.screenshots
                        if screenshot.screenType == ScreenType.TACTIC_FORMATION.value
                    ]
                    latest = (
                        max(formations, key=lambda item: (item.date, item.id))
                        if formations
                        else None
                    )
                    records.append(
                        TacticRecord(
                            tactic.name,
                            len(tactic.screenshots),
                            latest.imageFilename if latest else None,
                            hasStructuredData=tactic.structuredDefinition is not None,
                            hasObjectModelData=False,
                        )
                    )
                return sorted(records, key=lambda record: record.name.casefold())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list tactic records: {exc}") from exc

    def tacticDetailRecord(self, tacticName: str) -> TacticDetailRecord | None:
        """Return persisted detail facts for one tactic without invoking OCR."""

        normalizedName = tacticName.strip().casefold()
        try:
            with Session(self.engine) as session:
                tactic = session.scalar(
                    select(Tactic)
                    .where(Tactic.normalizedName == normalizedName)
                    .options(
                        selectinload(Tactic.screenshots).selectinload(
                            TacticScreenshot.importSession
                        ),
                        selectinload(Tactic.squadApplications).selectinload(
                            SquadTacticApplication.squad
                        ),
                    )
                )
                if tactic is None:
                    return None
                imports = [screenshot.importSession for screenshot in tactic.screenshots]
                capturedScreenTypes = tuple(
                    sorted({screenshot.screenType for screenshot in tactic.screenshots})
                )
                updatedAt = (
                    max(imports, key=lambda item: (item.date, item.id)).date if imports else None
                )
                return TacticDetailRecord(
                    name=tactic.name,
                    capturedScreenTypes=capturedScreenTypes,
                    captureCount=len(tactic.screenshots),
                    assignedSquads=tuple(
                        sorted(
                            (application.squad.name for application in tactic.squadApplications),
                            key=str.casefold,
                        )
                    ),
                    updatedAt=updatedAt,
                )
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to load tactic details: {exc}") from exc

    def squadsList(self) -> list[str]:
        """Return recognised squad names alphabetically."""

        try:
            with Session(self.engine) as session:
                return list(session.scalars(select(Squad.name).order_by(Squad.name)).all())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squads: {exc}") from exc

    def squadRecords(self) -> list[SquadRecord]:
        """Return squad-management records with capture and player counts."""

        try:
            with Session(self.engine) as session:
                squads = session.scalars(
                    select(Squad)
                    .options(
                        selectinload(Squad.screenshots)
                        .selectinload(SquadScreenshot.importSession)
                        .selectinload(ImportSession.players),
                        selectinload(Squad.clubScreenshots).selectinload(
                            SquadClubScreenshot.importSession
                        ),
                    )
                    .order_by(Squad.name)
                ).all()
                records = []
                for squad in squads:
                    latestClub = (
                        max(
                            (item.importSession for item in squad.clubScreenshots),
                            key=lambda item: (item.date, item.id),
                        )
                        if squad.clubScreenshots
                        else None
                    )
                    records.append(
                        SquadRecord(
                            squad.name,
                            len(squad.screenshots),
                            sum(
                                len(screenshot.importSession.players)
                                for screenshot in squad.screenshots
                            ),
                            latestClub.imageFilename if latestClub else None,
                        )
                    )
                return records
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squad records: {exc}") from exc

    def squadPlayerRecords(self, squadName: str) -> list[SquadPlayerRecord]:
        """Return stored players and their source screenshots for one squad."""

        normalizedName = squadName.strip().casefold()
        try:
            with Session(self.engine) as session:
                rows = session.execute(
                    select(Player, ImportSession)
                    .join(ImportSession, Player.importSessionId == ImportSession.id)
                    .join(
                        SquadScreenshot,
                        SquadScreenshot.importSessionId == ImportSession.id,
                    )
                    .join(Squad, SquadScreenshot.squadId == Squad.id)
                    .where(Squad.normalizedName == normalizedName)
                    .order_by(Player.name, ImportSession.date.desc())
                ).all()
                return [
                    SquadPlayerRecord(
                        player.name,
                        player.positions,
                        player.ca,
                        player.pa,
                        player.confidence,
                        importSession.date,
                        importSession.imageFilename,
                    )
                    for player, importSession in rows
                ]
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squad players: {exc}") from exc

    def squadClean(self, squadName: str) -> SquadCleanupRecord:
        """Correct and merge only unambiguous duplicate players in a stored squad."""

        normalizedName = squadName.strip().casefold()
        validator = PlayerValidator()
        try:
            with self._sessionFactory.begin() as session:
                players = list(
                    session.scalars(
                        select(Player)
                        .join(ImportSession, Player.importSessionId == ImportSession.id)
                        .join(
                            SquadScreenshot,
                            SquadScreenshot.importSessionId == ImportSession.id,
                        )
                        .join(Squad, SquadScreenshot.squadId == Squad.id)
                        .where(Squad.normalizedName == normalizedName)
                        .options(selectinload(Player.attributes))
                        .order_by(Player.id)
                    ).all()
                )
                extracted = [
                    ExtractedPlayer(
                        player.name,
                        player.positions,
                        player.ca,
                        player.pa,
                        {
                            attribute.attributeName: attribute.attributeValue
                            for attribute in player.attributes
                        },
                        player.confidence,
                    )
                    for player in players
                ]
                sanity = validator.correctAll(
                    extracted,
                    context=f"stored squad={squadName}",
                )
                for player, corrected in zip(players, sanity.players, strict=True):
                    player.name = corrected.name
                    player.positions = corrected.positions
                    player.ca = corrected.ca
                    player.pa = corrected.pa

                contextualCorrections = 0
                removedArtifacts: set[int] = set()
                canonical = [
                    player
                    for player in players
                    if 1 <= len(player.name.split()) <= 3
                    and player.ca.isdigit()
                    and player.pa.isdigit()
                ]
                for player in players:
                    if len(player.name.split()) <= 3:
                        continue
                    normalizedPlayerName = " ".join(player.name.casefold().split())
                    caValues = set(re.findall(r"\d{1,3}", player.ca))
                    paValues = set(re.findall(r"\d{1,3}", player.pa))
                    matches = [
                        candidate
                        for candidate in canonical
                        if " ".join(candidate.name.casefold().split()) in normalizedPlayerName
                        and candidate.ca in caValues
                        and candidate.pa in paValues
                    ]
                    identities = {
                        (candidate.name.casefold(), candidate.ca, candidate.pa): candidate
                        for candidate in matches
                    }
                    if len(identities) == 1:
                        candidate = next(iter(identities.values()))
                        oldValues = (player.name, player.positions, player.ca, player.pa)
                        newValues = (
                            candidate.name,
                            candidate.positions,
                            candidate.ca,
                            candidate.pa,
                        )
                        for field, old, new in zip(
                            ("name", "positions", "ca", "pa"),
                            oldValues,
                            newValues,
                            strict=True,
                        ):
                            if old == new:
                                continue
                            setattr(player, field, new)
                            contextualCorrections += 1
                            logger.action(
                                "stored squad contextual correction squad=%r playerId=%d "
                                "field=%s old=%r new=%r",
                                squadName,
                                player.id,
                                field,
                                old,
                                new,
                            )
                    elif len(identities) > 1:
                        removedArtifacts.add(player.id)
                        session.delete(player)
                        logger.action(
                            "stored squad composite row removed squad=%r playerId=%d "
                            "name=%r matchedPlayers=%r",
                            squadName,
                            player.id,
                            player.name,
                            [candidate.name for candidate in identities.values()],
                        )

                players = [player for player in players if player.id not in removedArtifacts]
                for index, left in enumerate(players):
                    if not left.ca.isdigit() or not left.pa.isdigit():
                        continue
                    for right in players[index + 1 :]:
                        if (left.ca, left.pa) != (right.ca, right.pa):
                            continue
                        leftName = " ".join(left.name.casefold().split())
                        rightName = " ".join(right.name.casefold().split())
                        if leftName == rightName:
                            continue
                        similarity = SequenceMatcher(None, leftName, rightName).ratio()
                        if similarity < 0.94:
                            continue
                        preferred = max((left, right), key=self._storedPlayerQuality)
                        corrected = right if preferred is left else left
                        oldName = corrected.name
                        corrected.name = preferred.name
                        contextualCorrections += 1
                        logger.action(
                            "stored squad near-name correction squad=%r playerId=%d "
                            "old=%r new=%r ca=%s pa=%s similarity=%.3f",
                            squadName,
                            corrected.id,
                            oldName,
                            corrected.name,
                            corrected.ca,
                            corrected.pa,
                            similarity,
                        )

                groups: dict[tuple[str, str, str], list[Player]] = {}
                for player in players:
                    identity = (
                        " ".join(player.name.casefold().split()),
                        player.ca,
                        player.pa,
                    )
                    groups.setdefault(identity, []).append(player)

                mergedCount = len(removedArtifacts)
                for identity, duplicates in groups.items():
                    if not all(identity) or len(duplicates) < 2:
                        continue
                    survivor = max(duplicates, key=self._storedPlayerQuality)
                    for duplicate in duplicates:
                        if duplicate is survivor:
                            continue
                        self._storedPlayerMerge(survivor, duplicate)
                        session.delete(duplicate)
                        mergedCount += 1
                        logger.action(
                            "stored squad duplicate merged squad=%r keptPlayerId=%d "
                            "removedPlayerId=%d player=%r ca=%s pa=%s",
                            squadName,
                            survivor.id,
                            duplicate.id,
                            survivor.name,
                            survivor.ca,
                            survivor.pa,
                        )

                identitiesByName: dict[str, set[tuple[str, str]]] = {}
                for identity in groups:
                    if all(identity):
                        identitiesByName.setdefault(identity[0], set()).add(identity[1:])
                ambiguousCount = sum(
                    len(identities) - 1
                    for identities in identitiesByName.values()
                    if len(identities) > 1
                )
                remainingCount = len(players) - (mergedCount - len(removedArtifacts))
                correctedCount = len(sanity.corrections) + contextualCorrections
            logger.action(
                "stored squad cleaned squad=%r corrections=%d merged=%d "
                "ambiguous=%d remaining=%d",
                squadName,
                correctedCount,
                mergedCount,
                ambiguousCount,
                remainingCount,
            )
            return SquadCleanupRecord(
                correctedCount,
                mergedCount,
                ambiguousCount,
                remainingCount,
            )
        except SQLAlchemyError as exc:
            logger.exception("stored squad cleanup failed squad=%r", squadName)
            raise DatabaseError(f"Unable to clean squad: {exc}") from exc

    @staticmethod
    def _storedPlayerMerge(survivor: Player, duplicate: Player) -> None:
        """Fill missing survivor fields from one exact-identity duplicate."""

        survivor.confidence = max(survivor.confidence, duplicate.confidence)
        if not survivor.positions:
            survivor.positions = duplicate.positions
        attributes = {item.attributeName: item for item in survivor.attributes}
        for source in duplicate.attributes:
            target = attributes.get(source.attributeName)
            if target is None:
                survivor.attributes.append(
                    AttributeSnapshot(
                        attributeName=source.attributeName,
                        attributeValue=source.attributeValue,
                    )
                )
            elif target.attributeValue is None and source.attributeValue is not None:
                target.attributeValue = source.attributeValue

    @staticmethod
    def _storedPlayerQuality(player: Player) -> tuple[int, float, int]:
        populated = sum(item.attributeValue is not None for item in player.attributes)
        return populated, player.confidence, -player.id

    def tacticsDelete(self, tacticNames: list[str]) -> DeletionRecord:
        """Delete selected tactics and their owned import sessions atomically."""

        normalizedNames = {name.strip().casefold() for name in tacticNames if name.strip()}
        try:
            with self._sessionFactory.begin() as session:
                tactics = session.scalars(
                    select(Tactic)
                    .where(Tactic.normalizedName.in_(normalizedNames))
                    .options(
                        selectinload(Tactic.screenshots).selectinload(
                            TacticScreenshot.importSession
                        )
                    )
                ).all()
                imports = [
                    screenshot.importSession
                    for tactic in tactics
                    for screenshot in tactic.screenshots
                ]
                paths = tuple(item.imageFilename for item in imports)
                for tactic in tactics:
                    session.delete(tactic)
                session.flush()
                for importSession in imports:
                    session.delete(importSession)
            logger.action(
                "tactics deleted names=%r count=%d captures=%d",
                tacticNames,
                len(tactics),
                len(paths),
            )
            return DeletionRecord(len(tactics), paths)
        except SQLAlchemyError as exc:
            logger.exception("tactic deletion database write failed")
            raise DatabaseError(f"Unable to delete tactics: {exc}") from exc

    def squadsDelete(self, squadNames: list[str]) -> DeletionRecord:
        """Delete selected squads and their owned import sessions atomically."""

        normalizedNames = {name.strip().casefold() for name in squadNames if name.strip()}
        try:
            with self._sessionFactory.begin() as session:
                squads = session.scalars(
                    select(Squad)
                    .where(Squad.normalizedName.in_(normalizedNames))
                    .options(
                        selectinload(Squad.screenshots).selectinload(SquadScreenshot.importSession),
                        selectinload(Squad.clubScreenshots).selectinload(
                            SquadClubScreenshot.importSession
                        ),
                    )
                ).all()
                imports = [
                    screenshot.importSession for squad in squads for screenshot in squad.screenshots
                ]
                imports.extend(
                    screenshot.importSession
                    for squad in squads
                    for screenshot in squad.clubScreenshots
                )
                paths = tuple(item.imageFilename for item in imports)
                for squad in squads:
                    session.delete(squad)
                session.flush()
                for importSession in imports:
                    session.delete(importSession)
            logger.action(
                "squads deleted names=%r count=%d captures=%d",
                squadNames,
                len(squads),
                len(paths),
            )
            return DeletionRecord(len(squads), paths)
        except SQLAlchemyError as exc:
            logger.exception("squad deletion database write failed")
            raise DatabaseError(f"Unable to delete squads: {exc}") from exc

    def playerNamesForSquad(self, squadName: str) -> set[str]:
        """Return player names previously confirmed for a squad."""

        normalizedName = squadName.strip().casefold()
        try:
            with Session(self.engine) as session:
                names = session.scalars(
                    select(Player.name)
                    .join(ImportSession, Player.importSessionId == ImportSession.id)
                    .join(
                        SquadScreenshot,
                        SquadScreenshot.importSessionId == ImportSession.id,
                    )
                    .join(Squad, SquadScreenshot.squadId == Squad.id)
                    .where(Squad.normalizedName == normalizedName)
                ).all()
            return set(names)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to inspect squad players: {exc}") from exc

    def tacticApplyToSquad(
        self,
        squadName: str,
        tacticName: str,
    ) -> SquadTacticApplication:
        """Create or return a deliberate squad-to-tactic application."""

        try:
            created = False
            with self._sessionFactory.begin() as session:
                squad = session.scalar(
                    select(Squad).where(Squad.normalizedName == squadName.strip().casefold())
                )
                if squad is None:
                    raise DatabaseError(f"Unknown squad: {squadName}")
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == tacticName.strip().casefold())
                )
                if tactic is None:
                    raise DatabaseError(f"Unknown tactic: {tacticName}")
                application = session.scalar(
                    select(SquadTacticApplication).where(
                        SquadTacticApplication.squadId == squad.id,
                        SquadTacticApplication.tacticId == tactic.id,
                    )
                )
                if application is None:
                    application = SquadTacticApplication(squad=squad, tactic=tactic)
                    session.add(application)
                    created = True
            if created:
                logger.action(
                    "tactic applied squad=%r tactic=%r application=%s",
                    squadName,
                    tacticName,
                    application.id,
                )
            return application
        except SQLAlchemyError as exc:
            logger.exception("squad tactic application database write failed")
            raise DatabaseError(f"Unable to apply tactic to squad: {exc}") from exc

    def playersList(self) -> list[Player]:
        """Return stored players newest first for the Players view."""

        try:
            with Session(self.engine) as session:
                return list(
                    session.scalars(
                        select(Player).order_by(Player.dateImported.desc(), Player.name)
                    ).all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list players: {exc}") from exc
