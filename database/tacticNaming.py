"""Persist user-owned tactic display-name changes without touching evidence."""

from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import ObjectModelTactic, Tactic


class TacticRenameError(RuntimeError):
    """Raised when a tactic cannot be renamed safely."""


def tacticRename(engine: Engine, oldName: str, newName: str) -> str:
    """Rename the tactic identity and linked object model atomically.

    Screenshot, structured extraction and squad-application rows are linked by
    tactic ID, so a display-name change must not regenerate or supersede them.
    """

    oldClean = oldName.strip()
    newClean = newName.strip()
    if not newClean:
        raise TacticRenameError("A tactic name is required")
    oldNormalized = oldClean.casefold()
    newNormalized = newClean.casefold()
    try:
        with Session(engine) as session, session.begin():
            tactic = session.scalar(
                select(Tactic).where(Tactic.normalizedName == oldNormalized),
            )
            if tactic is None:
                raise TacticRenameError(f"Tactic {oldClean!r} was not found")
            conflict = session.scalar(
                select(Tactic).where(
                    Tactic.normalizedName == newNormalized,
                    Tactic.id != tactic.id,
                )
            )
            if conflict is not None:
                raise TacticRenameError(f"A tactic named {newClean!r} already exists")
            tactic.name = newClean
            tactic.normalizedName = newNormalized
            model = session.scalar(
                select(ObjectModelTactic).where(ObjectModelTactic.sourceTacticId == tactic.id)
            )
            if model is not None:
                modelConflict = session.scalar(
                    select(ObjectModelTactic).where(
                        ObjectModelTactic.normalizedName == newNormalized,
                        ObjectModelTactic.id != model.id,
                    )
                )
                if modelConflict is not None:
                    raise TacticRenameError(
                        f"A saved tactic model named {newClean!r} already exists"
                    )
                model.name = newClean
                model.normalizedName = newNormalized
    except TacticRenameError:
        raise
    except SQLAlchemyError as exc:
        raise TacticRenameError(f"Unable to rename tactic: {exc}") from exc
    return newClean
