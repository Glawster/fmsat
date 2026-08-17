"""Persistence for historical OCR-zone geometry observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from fmsat.core.ocrZoneHistory import (
    OcrZoneDriftClassifier,
    OcrZoneDriftResult,
    OcrZoneGeometry,
)


metadata = MetaData()
observations = Table(
    "ocr_zone_observations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("observed_at", DateTime, nullable=False),
    Column("source_import_session_id", Integer, nullable=True, index=True),
    Column("screen_type", String(64), nullable=False, index=True),
    Column("layout_profile", String(100), nullable=False, index=True),
    Column("zone_name", String(120), nullable=False, index=True),
    Column("x", Float, nullable=False),
    Column("y", Float, nullable=False),
    Column("width", Float, nullable=False),
    Column("height", Float, nullable=False),
    Column("classification", String(32), nullable=False),
    Column("accepted_baseline", Boolean, nullable=False, default=False),
)


@dataclass(frozen=True, slots=True)
class OcrZoneObservationRecord:
    """One detached historical geometry observation."""

    geometry: OcrZoneGeometry
    classification: str
    acceptedBaseline: bool
    observedAt: datetime


class OcrZoneHistoryStore:
    """Append-only historical store; anomalous rows are never baseline evidence."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        metadata.create_all(engine, tables=[observations], checkfirst=True)

    def history(
        self,
        screenType: str,
        layoutProfile: str,
        zoneName: str,
    ) -> tuple[OcrZoneObservationRecord, ...]:
        """Return accepted baseline observations for one comparable zone."""

        statement = (
            select(observations)
            .where(and_(
                observations.c.screen_type == screenType,
                observations.c.layout_profile == layoutProfile,
                observations.c.zone_name == zoneName,
                observations.c.accepted_baseline.is_(True),
            ))
            .order_by(observations.c.observed_at, observations.c.id)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(
            OcrZoneObservationRecord(
                OcrZoneGeometry(row["x"], row["y"], row["width"], row["height"]),
                row["classification"],
                bool(row["accepted_baseline"]),
                row["observed_at"],
            )
            for row in rows
        )

    def observe(
        self,
        screenType: str,
        layoutProfile: str,
        zoneName: str,
        geometry: OcrZoneGeometry,
        classifier: OcrZoneDriftClassifier,
        *,
        validated: bool,
        sourceImportSessionId: int | None = None,
    ) -> OcrZoneDriftResult:
        """Classify and append one observation without teaching from anomalies."""

        history = self.history(screenType, layoutProfile, zoneName)
        result = classifier.classify(
            geometry,
            tuple(item.geometry for item in history),
        )
        accepted = validated and result.state != "anomalous"
        self.record(
            screenType,
            layoutProfile,
            zoneName,
            geometry,
            result.state,
            accepted,
            sourceImportSessionId,
        )
        return result

    def record(
        self,
        screenType: str,
        layoutProfile: str,
        zoneName: str,
        geometry: OcrZoneGeometry,
        classification: str,
        acceptedBaseline: bool,
        sourceImportSessionId: int | None = None,
    ) -> None:
        """Append an observation without deleting previous geometry evidence."""

        with self.engine.begin() as connection:
            connection.execute(insert(observations).values(
                observed_at=datetime.now(),
                source_import_session_id=sourceImportSessionId,
                screen_type=screenType,
                layout_profile=layoutProfile,
                zone_name=zoneName,
                x=geometry.x,
                y=geometry.y,
                width=geometry.width,
                height=geometry.height,
                classification=classification,
                accepted_baseline=acceptedBaseline,
            ))
