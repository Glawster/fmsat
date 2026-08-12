"""Validation of OCR-derived player records."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fmsat.core.logUtils import getLogger

from ..parser import ExtractedPlayer

logger = getLogger()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One actionable validation problem."""

    field: str
    message: str
    blocking: bool = False


@dataclass(frozen=True, slots=True)
class PlayerCorrection:
    """One deterministic OCR correction applied before review."""

    player: str
    field: str
    original: str
    corrected: str


@dataclass(frozen=True, slots=True)
class SquadSanityReport:
    """Corrected rows and all remaining review issues for one squad capture."""

    players: tuple[ExtractedPlayer, ...]
    corrections: tuple[PlayerCorrection, ...]
    issues: tuple[tuple[int, ValidationIssue], ...]

    @property
    def blockingIssues(self) -> tuple[tuple[int, ValidationIssue], ...]:
        return tuple(item for item in self.issues if item[1].blocking)

    @property
    def missingPlayers(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    row
                    for row, issue in self.issues
                    if issue.message == "Attribute value is missing"
                }
            )
        )

    @property
    def missingByPlayer(self) -> tuple[tuple[int, str, tuple[str, ...]], ...]:
        missing: dict[int, list[str]] = {}
        for row, issue in self.issues:
            if issue.message == "Attribute value is missing":
                missing.setdefault(row, []).append(issue.field)
        return tuple(
            (row, self.players[row].name, tuple(fields))
            for row, fields in sorted(missing.items())
        )


class PlayerValidator:
    """Checks required fields, confidence, and Football Manager attribute ranges."""

    def __init__(self, confidenceThreshold: float = 0.95) -> None:
        self.confidenceThreshold = confidenceThreshold

    def isLowConfidence(self, player: ExtractedPlayer) -> bool:
        """Return whether a row should be highlighted for review."""

        return player.confidence < self.confidenceThreshold

    def validate(self, player: ExtractedPlayer) -> list[ValidationIssue]:
        """Return all issues rather than failing on the first OCR problem."""

        issues: list[ValidationIssue] = []
        if not player.name.strip():
            issues.append(ValidationIssue("name", "Player name is required", True))
        elif not re.fullmatch(r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ' -]*", player.name):
            issues.append(
                ValidationIssue(
                    "name",
                    "Player name contains suspicious leading or trailing characters",
                    True,
                )
            )
        if len(player.name.split()) > 3:
            issues.append(
                ValidationIssue(
                    "name",
                    "Player name may contain merged player rows",
                    True,
                )
            )
        for field, value in (("ca", player.ca), ("pa", player.pa)):
            if re.fullmatch(r"\d{1,3}", value) is None:
                issues.append(
                    ValidationIssue(field, f"{field.upper()} must be one integer", True)
                )
            elif not 1 <= int(value) <= 200:
                issues.append(
                    ValidationIssue(field, f"{field.upper()} must be between 1 and 200", True)
                )
        if player.ca.isdigit() and player.pa.isdigit() and int(player.ca) > int(player.pa):
            issues.append(ValidationIssue("ca", "CA cannot exceed PA", True))
        if not self._positionsValid(player.positions):
            issues.append(
                ValidationIssue("positions", "Position format is not recognised", True)
            )
        if self.isLowConfidence(player):
            issues.append(
                ValidationIssue(
                    "confidence",
                    f"Confidence is below {self.confidenceThreshold:.0%}",
                )
            )
        for name, value in player.attributes.items():
            if value is None:
                issues.append(ValidationIssue(name, "Attribute value is missing"))
            elif not 1 <= value <= 20:
                issues.append(
                    ValidationIssue(name, "Attribute must be between 1 and 20", True)
                )
        return issues

    def correctAll(
        self,
        players: list[ExtractedPlayer],
        *,
        context: str,
    ) -> SquadSanityReport:
        """Apply safe OCR corrections and report every remaining issue."""

        correctedPlayers: list[ExtractedPlayer] = []
        corrections: list[PlayerCorrection] = []
        issues: list[tuple[int, ValidationIssue]] = []
        for row, player in enumerate(players):
            corrected, playerCorrections = self._correct(player, context)
            correctedPlayers.append(corrected)
            corrections.extend(playerCorrections)
            issues.extend((row, issue) for issue in self.validate(corrected))
        identities: dict[tuple[str, str, str], int] = {}
        for row, player in enumerate(correctedPlayers):
            identity = (self._nameNormalize(player.name), player.ca, player.pa)
            if not identity[0] or not player.ca.isdigit() or not player.pa.isdigit():
                continue
            if identity in identities:
                firstRow = identities[identity]
                issue = ValidationIssue(
                    "name",
                    f"Possible duplicate of row {firstRow + 1}",
                    True,
                )
                issues.append((row, issue))
                logger.warning(
                    "sanity duplicate context=%s row=%d firstRow=%d player=%r ca=%s pa=%s",
                    context,
                    row + 1,
                    firstRow + 1,
                    player.name,
                    player.ca,
                    player.pa,
                )
            else:
                identities[identity] = row
        report = SquadSanityReport(
            tuple(correctedPlayers),
            tuple(corrections),
            tuple(issues),
        )
        for row, name, fields in report.missingByPlayer:
            logger.info(
                "sanity missing data context=%s row=%d player=%r fields=%s",
                context,
                row + 1,
                name,
                ",".join(fields),
            )
        return report

    def duplicatesMerge(
        self,
        players: list[ExtractedPlayer],
        *,
        context: str,
    ) -> tuple[list[ExtractedPlayer], int]:
        """Merge only rows with the same cleaned name, CA, and PA."""

        merged: dict[tuple[str, str, str], ExtractedPlayer] = {}
        order: list[tuple[str, str, str]] = []
        mergedCount = 0
        for row, player in enumerate(players):
            identity = (self._nameNormalize(player.name), player.ca, player.pa)
            if not all(identity):
                identity = (f"__invalid_row_{row}", player.ca, player.pa)
            existing = merged.get(identity)
            if existing is None:
                merged[identity] = player
                order.append(identity)
                continue
            preferred, other = (
                (player, existing)
                if self._playerQuality(player) > self._playerQuality(existing)
                else (existing, player)
            )
            attributes = dict(other.attributes)
            attributes.update(
                {name: value for name, value in preferred.attributes.items() if value is not None}
            )
            merged[identity] = ExtractedPlayer(
                preferred.name,
                preferred.positions or other.positions,
                preferred.ca,
                preferred.pa,
                attributes,
                max(preferred.confidence, other.confidence),
            )
            mergedCount += 1
            logger.action(
                "sanity duplicate merged context=%s player=%r ca=%s pa=%s",
                context,
                preferred.name,
                preferred.ca,
                preferred.pa,
            )
        return [merged[identity] for identity in order], mergedCount

    def _correct(
        self,
        player: ExtractedPlayer,
        context: str,
    ) -> tuple[ExtractedPlayer, list[PlayerCorrection]]:
        cleanedName = self._nameClean(player.name)
        simplePlayerName = 1 <= len(cleanedName.split()) <= 3
        values = {
            "name": cleanedName,
            "positions": self._positionsClean(player.positions),
            "ca": self._abilityClean(player.ca, simplePlayerName),
            "pa": self._abilityClean(player.pa, simplePlayerName),
        }
        corrections: list[PlayerCorrection] = []
        for field, original in (
            ("name", player.name),
            ("positions", player.positions),
            ("ca", player.ca),
            ("pa", player.pa),
        ):
            corrected = values[field]
            if corrected == original:
                continue
            correction = PlayerCorrection(player.name, field, original, corrected)
            corrections.append(correction)
            logger.action(
                "sanity correction context=%s player=%r field=%s old=%r new=%r",
                context,
                player.name,
                field,
                original,
                corrected,
            )
        return (
            ExtractedPlayer(
                values["name"],
                values["positions"],
                values["ca"],
                values["pa"],
                dict(player.attributes),
                player.confidence,
            ),
            corrections,
        )

    @classmethod
    def _nameClean(cls, value: str) -> str:
        cleaned = value.strip().rstrip(".").strip()
        originalWords = cleaned.split()
        if len(originalWords) >= 4 and len(originalWords) % 2 == 0:
            halfway = len(originalWords) // 2
            first = cls._iconTokensRemove(originalWords[:halfway])
            second = cls._iconTokensRemove(originalWords[halfway:])
            if [word.casefold() for word in first] == [word.casefold() for word in second]:
                cleaned = " ".join(first)
        cleaned = re.sub(r"^(?:Oe|Qe|Re)\s+(?=[A-Z])", "", cleaned)
        cleaned = re.sub(r"^De\s+(?=[A-Z][a-z]+\s+[A-Za-z])", "", cleaned)
        cleaned = re.sub(r"^A\s+(?=[A-Z][a-z]+(?:\s|$))", "", cleaned)
        cleaned = re.sub(r"^(?:3A|[ADOQ])(?=[A-Z][a-z])", "", cleaned)
        cleaned = re.sub(r"^e(?=[a-z]+(?:\s|$))", "", cleaned)
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        cleaned = " ".join(
            word.capitalize() if word.islower() else word for word in cleaned.split()
        )
        return re.sub(r"\bMc\s+([A-Z][a-z]+)\b", r"Mc\1", cleaned)

    @staticmethod
    def _abilityClean(value: str, allowMultiple: bool) -> str:
        cleaned = value.strip()
        match = re.fullmatch(r"[^\s]*[A-Za-z][^\s]*\s+(\d{1,3})", cleaned)
        if match is not None:
            return match.group(1)
        if allowMultiple:
            values = re.fullmatch(r"\d{1,3}(?:\s+\d{1,3})+", cleaned)
            if values is not None:
                return cleaned.split()[-1]
        return cleaned

    @staticmethod
    def _iconTokensRemove(words: list[str]) -> list[str]:
        return words[1:] if words and words[0] in {"Oe", "Qe", "Re", "A"} else words

    @staticmethod
    def _positionsClean(value: str) -> str:
        cleaned = value.strip().upper()
        cleaned = re.sub(r"\s*\(\s*", " (", cleaned)
        cleaned = re.sub(r"\s*\)", ")", cleaned)
        cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
        cleaned = re.sub(r"\s*/\s*", "/", cleaned)
        cleaned = re.sub(r"\)\s*[.;]\s*(?=(?:GK|D|WB|DM|M|AM|ST)\b)", "), ", cleaned)
        cleaned = " ".join(cleaned.split())
        if PlayerValidator._positionsValid(cleaned):
            return cleaned
        for match in re.finditer(r"\b(?:GK|D|WB|DM|M|AM|ST)\b", cleaned):
            candidate = cleaned[match.start() :]
            if PlayerValidator._positionsValid(candidate):
                return candidate
        return cleaned

    @staticmethod
    def _positionsValid(value: str) -> bool:
        if not value:
            return False
        return (
            re.fullmatch(
                r"(?:GK|(?:D|WB|DM|M|AM|ST)(?:/(?:D|WB|DM|M|AM|ST))*"
                r"(?: \([LRC]+\))?)(?:, (?:GK|(?:D|WB|DM|M|AM|ST)"
                r"(?:/(?:D|WB|DM|M|AM|ST))*(?: \([LRC]+\))?))*",
                value,
            )
            is not None
        )

    @staticmethod
    def _nameNormalize(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _playerQuality(player: ExtractedPlayer) -> tuple[int, float]:
        populated = sum(value is not None for value in player.attributes.values())
        return populated, player.confidence
