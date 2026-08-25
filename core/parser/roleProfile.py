"""Football Manager role-profile screenshot evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..config import AttributeDefinition
from ..ocr import OcrEngine, OcrResult
from .squadAttributes import ParserError
from .tacticModels import TacticalPhase


@dataclass(frozen=True, slots=True)
class RoleProfileEvidence:
    """Facts observed on one Football Manager role-profile screen.

    ``keyAttributes`` records which attributes Football Manager identifies as
    important to the role. ``displayedPlayerAttributes`` contains the selected
    player's visible ratings; those ratings are evidence about the player and
    must never be interpreted as role weights.
    """

    position: str
    roleName: str
    phase: TacticalPhase | None = None
    abbreviation: str | None = None
    behaviours: tuple[str, ...] = ()
    description: str | None = None
    keyAttributes: tuple[str, ...] = ()
    playerInstructions: tuple[str, ...] = ()
    displayedPlayerAttributes: dict[str, int] = field(default_factory=dict)
    suitabilityStars: float | None = None
    sourceImport: str | None = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Reject impossible displayed values without inventing missing data."""

        invalidAttributes = {
            name: value
            for name, value in self.displayedPlayerAttributes.items()
            if value < 1 or value > 20
        }
        if invalidAttributes:
            raise ValueError(
                "Displayed Football Manager attributes must be between 1 and 20: "
                f"{invalidAttributes}"
            )
        if self.suitabilityStars is not None and not 0 <= self.suitabilityStars <= 5:
            raise ValueError("Displayed role suitability must be between 0 and 5 stars")

    def playerValuesForKeyAttributes(self) -> dict[str, int]:
        """Return visible player ratings limited to the role's key attributes."""

        return {
            attribute: self.displayedPlayerAttributes[attribute]
            for attribute in self.keyAttributes
            if attribute in self.displayedPlayerAttributes
        }


@dataclass(frozen=True, slots=True)
class RoleKnowledgeGap:
    """A distinct tactic role and position lacking factual role knowledge."""

    role: str
    position: str
    slotIds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleDefinitionDraft:
    """Reviewed factual role data eligible for confirmation as YAML."""

    roleID: int
    displayName: str
    phase: TacticalPhase
    abbreviations: tuple[str, ...]
    positions: tuple[str, ...]
    description: str | None
    behaviours: tuple[str, ...]
    keyAttributes: tuple[str, ...]
    playerInstructions: tuple[str, ...]
    sourceImport: str | None


class RoleProfileParser:
    """Extract factual evidence from a Football Manager role-profile screen."""

    def __init__(
        self,
        ocr: OcrEngine,
        vocabulary,
        attributes: tuple[AttributeDefinition, ...],
    ) -> None:
        self.ocr = ocr
        self.vocabulary = vocabulary
        self.attributes = attributes

    def parse(self, image: np.ndarray) -> RoleProfileEvidence:
        """Return reviewable evidence without deriving weights or targets."""

        results = [result for result in self.ocr.recognize(image) if result.text.strip()]
        if not results:
            raise ParserError("No role-profile text could be extracted")
        position = self._positionFind(results)
        phase = self._phaseRead(results)
        roleName, abbreviation = self._roleRead(results, image.shape[1])
        behaviours = self._behavioursRead(results, image.shape[1])
        keyAttributes, displayedValues = self._keyAttributesRead(results, image.shape[1])
        if not keyAttributes:
            raise ParserError("No Key Attributes could be extracted from the role profile")
        description = self._descriptionRead(results, image.shape[1], roleName, behaviours)
        instructions = self._instructionsRead(results, image.shape[1])
        confidenceValues = [result.confidence for result in results]
        return RoleProfileEvidence(
            position=position,
            roleName=roleName,
            phase=phase,
            abbreviation=abbreviation,
            behaviours=behaviours,
            description=description,
            keyAttributes=keyAttributes,
            playerInstructions=instructions,
            displayedPlayerAttributes=displayedValues,
            confidence=sum(confidenceValues) / len(confidenceValues),
        )

    def _behavioursRead(
        self,
        results: list[OcrResult],
        imageWidth: int,
    ) -> tuple[str, ...]:
        abilityIndex = self._headingIndex(results, "role ability")
        keyIndex = self._headingIndex(results, "key attributes")
        abilityY = None
        keyY = None
        if abilityIndex is not None and results[abilityIndex].center is not None:
            abilityY = results[abilityIndex].center[1]
        if keyIndex is not None and results[keyIndex].center is not None:
            keyY = results[keyIndex].center[1]
        behaviours = []
        for index, result in enumerate(results):
            indicators = self._indicatorsExtract(result.text)
            if not indicators:
                continue
            if result.center is not None:
                x, y = result.center
                # The selected role's indicators are rendered in the right detail
                # panel between the Role Ability and Key Attributes headings.
                if x < imageWidth * 0.33:
                    continue
                if abilityY is not None and y < abilityY - 10:
                    continue
                if keyY is not None and y >= keyY:
                    continue
            elif abilityIndex is not None and keyIndex is not None:
                if index <= abilityIndex or index >= keyIndex:
                    continue
            behaviours.extend(indicators)
        return tuple(dict.fromkeys(behaviours))

    def _indicatorsExtract(self, text: str) -> tuple[str, ...]:
        normalized = self.vocabulary.roleIndicatorNormalize(text)
        if normalized.resolved:
            return (normalized.value,)
        candidates = []
        normalizedText = f" {self._textKey(text)} "
        for alias, canonical in self.vocabulary.roleIndicators.items():
            if f" {alias} " in normalizedText:
                candidates.append(canonical)
        return tuple(dict.fromkeys(candidates))

    def _instructionsRead(
        self,
        results: list[OcrResult],
        imageWidth: int,
    ) -> tuple[str, ...]:
        headingIndex = self._headingIndex(results, "player instructions")
        if headingIndex is None:
            return ()
        headingY = results[headingIndex].center[1] if results[headingIndex].center else None
        instructions = []
        for result in results[headingIndex + 1 :]:
            text = result.text.strip()
            if not text or text.isdigit() or not any(character.isalpha() for character in text):
                continue
            if result.center is not None:
                x, y = result.center
                if x < imageWidth * 0.33:
                    continue
                if headingY is not None and y <= headingY:
                    continue
            instructions.append(self._identifier(text))
        return tuple(dict.fromkeys(instructions))

    def _keyAttributesRead(
        self,
        results: list[OcrResult],
        imageWidth: int,
    ) -> tuple[tuple[str, ...], dict[str, int]]:
        start = self._headingIndex(results, "key attributes")
        end = self._headingIndex(results, "player instructions")
        aliases = self._attributeAliases()
        if start is None:
            return self._keyAttributesWithoutHeading(results, end, imageWidth, aliases)

        # Retain the normal heading-anchored extraction when OCR sees the label.
        section = results[start + 1 : end]
        return self._attributesRead(section, aliases)

    def _attributeAliases(self) -> dict[str, str]:
        """Return the one attribute vocabulary used by both extraction paths."""

        aliases: dict[str, str] = {}
        for definition in self.attributes:
            aliases[self._textKey(definition.name)] = definition.name
            aliases[self._textKey(definition.name.replace("_", " "))] = definition.name
        return aliases

    def _attributesRead(
        self,
        section: list[OcrResult],
        aliases: dict[str, str],
    ) -> tuple[tuple[str, ...], dict[str, int]]:
        """Read recognized attribute names and their adjacent displayed ratings."""

        keys: list[str] = []
        values: dict[str, int] = {}
        for index, result in enumerate(section):
            attribute = aliases.get(self._textKey(result.text))
            if attribute is None:
                continue
            keys.append(attribute)
            rating = self._ratingNear(section, index, result)
            if rating is not None:
                values[attribute] = rating
        return tuple(dict.fromkeys(keys)), values

    def _keyAttributesWithoutHeading(
        self,
        results: list[OcrResult],
        instructionsIndex: int | None,
        imageWidth: int,
        aliases: dict[str, str],
    ) -> tuple[tuple[str, ...], dict[str, int]]:
        """Recover a missing heading only from a coherent detail-panel row block."""

        instructionsY = None
        if instructionsIndex is not None and results[instructionsIndex].center is not None:
            instructionsY = results[instructionsIndex].center[1]

        # Keep the original OCR ordering for _ratingNear, but exclude the role list and
        # everything at or below a recognized Player Instructions boundary.
        section = [
            result
            for result in results[:instructionsIndex]
            if result.center is not None
            and result.center[0] >= imageWidth * 0.33
            and (instructionsY is None or result.center[1] < instructionsY)
        ]
        rows: list[tuple[float, float, OcrResult, str, int]] = []
        for index, result in enumerate(section):
            attribute = aliases.get(self._textKey(result.text))
            if attribute is None:
                continue
            rating = self._ratingNear(section, index, result)
            if rating is None:
                continue
            x, y = result.center
            rows.append((y, x, result, attribute, rating))

        # Three rated rows are enough to establish a pattern, while isolated words or
        # pairs remain deliberately insufficient evidence. Row spacing is derived from
        # OCR box height, not from the description's changing screen position.
        rows.sort(key=lambda row: (row[0], row[1]))
        blocks: list[list[tuple[float, float, OcrResult, str, int]]] = []
        for row in rows:
            box = row[2].bounds
            rowHeight = max(1.0, float(box[3] - box[1]))
            if not blocks:
                blocks.append([row])
                continue
            previous = blocks[-1][-1]
            previousBox = previous[2].bounds
            previousHeight = max(1.0, float(previousBox[3] - previousBox[1]))
            maximumGap = max(rowHeight, previousHeight) * 4.5
            if 0 < row[0] - previous[0] <= maximumGap:
                blocks[-1].append(row)
            else:
                blocks.append([row])

        credible = [block for block in blocks if len(block) >= 3]
        if not credible:
            raise ParserError(
                "Neither the Key Attributes heading nor a credible attribute block was found"
            )
        largestSize = max(len(block) for block in credible)
        largest = [block for block in credible if len(block) == largestSize]
        if len(largest) != 1:
            raise ParserError("The role-profile attribute block is ambiguous")

        block = largest[0]
        keys = tuple(dict.fromkeys(row[3] for row in block))
        if len(keys) < 3:
            raise ParserError("The role-profile attribute block is ambiguous")
        return keys, {row[3]: row[4] for row in block}

    @staticmethod
    def _ratingNear(
        section: list[OcrResult],
        index: int,
        attributeResult: OcrResult,
    ) -> int | None:
        candidates = section[index + 1 : index + 3]
        for result in candidates:
            value = result.text.strip()
            if not value.isdigit() or not 1 <= int(value) <= 20:
                continue
            if attributeResult.center is None or result.center is None:
                return int(value)
            if abs(attributeResult.center[1] - result.center[1]) <= 12:
                return int(value)
        return None

    def _positionFind(self, results: list[OcrResult]) -> str:
        for result in results:
            normalized = self.vocabulary.positionNormalize(result.text)
            if normalized.resolved:
                return normalized.value
        for index, result in enumerate(results[:-1]):
            following = results[index + 1]
            for combined in (
                f"{result.text}{following.text}",
                f"{result.text} {following.text}",
            ):
                normalized = self.vocabulary.positionNormalize(combined)
                if normalized.resolved:
                    return normalized.value
        raise ParserError("No supported position could be extracted from the role profile")

    @staticmethod
    def _phaseRead(results: list[OcrResult]) -> TacticalPhase:
        text = " ".join(result.text for result in results).casefold()
        if "out of possession role" in text:
            return TacticalPhase.OUT_OF_POSSESSION
        if "in possession role" in text:
            return TacticalPhase.IN_POSSESSION
        raise ParserError("The role profile phase could not be extracted")

    def _descriptionRead(
        self,
        results: list[OcrResult],
        imageWidth: int,
        roleName: str,
        behaviours: tuple[str, ...],
    ) -> str | None:
        keyIndex = self._headingIndex(results, "key attributes")
        abilityIndex = self._headingIndex(results, "role ability")
        if keyIndex is None or abilityIndex is None:
            return None
        keyResult = results[keyIndex]
        abilityResult = results[abilityIndex]
        if keyResult.center is None or abilityResult.center is None:
            return None
        fragments = []
        for result in results:
            if result.center is None:
                continue
            x, y = result.center
            text = result.text.strip()
            # Role indicators are rendered above the narrative body and can be OCRed
            # as one combined sentence, so exclude them from the description payload.
            if self._descriptionContainsBehaviour(text, behaviours):
                continue
            if (
                x < imageWidth * 0.33
                or y <= abilityResult.center[1]
                or y >= keyResult.center[1]
                or self._textKey(text) == self._textKey(roleName)
                or len(text.split()) < 5
            ):
                continue
            fragments.append((y, x, text))
        if not fragments:
            return None
        return " ".join(text for _, _, text in sorted(fragments))

    def _descriptionContainsBehaviour(
        self,
        text: str,
        behaviours: tuple[str, ...],
    ) -> bool:
        if not behaviours:
            return False
        normalizedText = f" {self._textKey(text)} "
        for behaviour in behaviours:
            aliases = [
                alias
                for alias, canonical in self.vocabulary.roleIndicators.items()
                if canonical == behaviour and " " in alias
            ]
            for alias in aliases:
                if f" {alias} " in normalizedText:
                    return True
        return False

    def _roleFind(self, results: list[OcrResult]):
        combined = " ".join(result.text for result in results).casefold().replace("-", " ")
        matches = []
        for role in self.vocabulary.roles.values():
            display = role.displayName.casefold().replace("-", " ")
            count = combined.count(display)
            if count:
                matches.append((count, role))
        if not matches:
            raise ParserError("No supported role could be extracted from the role profile")
        matches.sort(key=lambda item: (-item[0], item[1].code))
        if len(matches) > 1 and matches[0][0] == matches[1][0]:
            raise ParserError("The selected role is ambiguous in the role-profile screenshot")
        return matches[0][1]

    def _roleRead(
        self,
        results: list[OcrResult],
        imageWidth: int,
    ) -> tuple[str, str | None]:
        abilityIndex = self._headingIndex(results, "role ability")
        if abilityIndex is not None and results[abilityIndex].center is not None:
            abilityY = results[abilityIndex].center[1]
            candidates = [
                result
                for result in results
                if result.center is not None
                and result.center[0] >= imageWidth * 0.33
                and result.center[1] < abilityY
                and result.text.strip()
            ]
            if candidates:
                recognized = [
                    (result, self.vocabulary.roleNormalize(result.text.strip(" \t\r\n.,:;")))
                    for result in candidates
                ]
                recognized = [item for item in recognized if item[1].resolved]
                if recognized:
                    result, normalized = max(
                        recognized,
                        key=lambda item: item[0].center[1],
                    )
                    title = result.text.strip(" \t\r\n.,:;")
                    role = self.vocabulary.roles[normalized.value]
                    abbreviation = role.abbreviations[0] if role.abbreviations else None
                    return title, abbreviation
                candidates = [
                    result for result in candidates if not self._abilityRating(result.text)
                ]
                if candidates:
                    title = max(candidates, key=lambda result: result.center[1]).text.strip(
                        " \t\r\n.,:;"
                    )
                    return title, None
        role = self._roleFind(results)
        abbreviation = role.abbreviations[0] if role.abbreviations else None
        return role.displayName, abbreviation

    @staticmethod
    def _abilityRating(value: str) -> bool:
        return RoleProfileParser._textKey(value) in {
            "awful",
            "poor",
            "below average",
            "decent",
            "fairly good",
            "good",
            "very good",
            "excellent",
            "outstanding",
        }

    @staticmethod
    def _headingIndex(results: list[OcrResult], heading: str) -> int | None:
        key = RoleProfileParser._textKey(heading)
        return next(
            (
                index
                for index, result in enumerate(results)
                if RoleProfileParser._textKey(result.text) == key
            ),
            None,
        )

    @staticmethod
    def _identifier(value: str) -> str:
        words = value.replace("-", " ").split()
        return words[0].casefold() + "".join(word.title() for word in words[1:])

    @staticmethod
    def _textKey(value: str) -> str:
        return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())
