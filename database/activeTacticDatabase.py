"""Persist the currently selected tactic while retaining squad tactic history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from fmsat.core.logUtils import getLogger

from .database import Database as BaseDatabase
from .database import DatabaseError
from .models import Squad, SquadTacticApplication, Tactic

logger = getLogger()


class Database(BaseDatabase):
    """Database gateway with most-recently-selected squad tactic semantics."""

    def squadAppliedTactics(self, squadName: str) -> tuple[str, ...]:
        """Return applied tactics with the currently selected tactic first."""

        normalizedName = squadName.strip().casefold()
        try:
            with self._sessionFactory() as session:
                return tuple(
                    session.scalars(
                        select(Tactic.name)
                        .join(SquadTacticApplication)
                        .join(Squad)
                        .where(Squad.normalizedName == normalizedName)
                        .order_by(
                            SquadTacticApplication.dateApplied.desc(),
                            Tactic.name,
                        )
                    ).all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to load squad tactics: {exc}") from exc

    def tacticApplyToSquad(
        self,
        squadName: str,
        tacticName: str,
    ) -> SquadTacticApplication:
        """Apply a tactic and persist it as the squad's current selection."""

        application = super().tacticApplyToSquad(squadName, tacticName)
        selectedAt = datetime.now()
        try:
            with self._sessionFactory.begin() as session:
                stored = session.get(SquadTacticApplication, application.id)
                if stored is None:
                    raise DatabaseError(
                        f"Unable to reload squad tactic application: {application.id}"
                    )
                stored.dateApplied = selectedAt
            application.dateApplied = selectedAt
            logger.action(
                "active tactic selected squad=%r tactic=%r application=%s",
                squadName,
                tacticName,
                application.id,
            )
            return application
        except SQLAlchemyError as exc:
            logger.exception("active squad tactic selection database write failed")
            raise DatabaseError(f"Unable to select tactic for squad: {exc}") from exc
