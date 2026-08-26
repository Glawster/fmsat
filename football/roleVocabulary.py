"""Shared role vocabulary helpers for parsers and model builders."""

from __future__ import annotations

from fmsat.core.logUtils import getLogger
from fmsat.core.parser import TacticVocabulary
from fmsat.football.roleIdentity import RoleIdentity

logger = getLogger()


class RoleVocabulary:
    """Normalize role text and resolve it to canonical role identities."""

    _vocabulary: TacticVocabulary | None = None

    @classmethod
    def identityResolve(cls, *candidates: str) -> RoleIdentity | None:
        """Resolve one role identity from any number of candidate strings."""

        logger.info(f"role identity candidates: {candidates!r}")
        explicitAliases = {
            "fullback": RoleIdentity.WB,
            "fb": RoleIdentity.WB,
        }
        # Prefer explicit enum-like tokens first (for example "DLP", "WB", "GK").
        for candidate in candidates:
            normalized = cls.normalize(candidate)
            if not normalized:
                continue
            if normalized in explicitAliases:
                resolved = explicitAliases[normalized]
                logger.info(f"role identity resolved directly: {candidate!r} -> {resolved.value}")
                return resolved
            direct = cls._identityFromToken(normalized)
            if direct is not None:
                logger.info(f"role identity resolved from token: {candidate!r} -> {direct.value}")
                return direct

        # Then resolve via configured role vocabulary, which includes canonical
        # role codes, display names, aliases, and known abbreviations.
        vocabulary = cls._vocabularyLoad()
        for candidate in candidates:
            normalized = vocabulary.roleNormalize(candidate)
            logger.info(
                "role vocabulary normalization: "
                f"{candidate!r} -> {normalized.value!r} resolved={normalized.resolved}"
            )
            if not normalized.resolved:
                continue
            role = vocabulary.roles.get(normalized.value)
            if role is None:
                logger.warning(
                    f"normalized role {normalized.value!r} is absent from loaded vocabulary"
                )
                continue
            logger.info(
                "role vocabulary definition: "
                f"code={role.code!r} abbreviations={role.abbreviations!r} "
                f"display={role.displayName!r}"
            )
            for abbreviation in role.abbreviations:
                mapped = cls._identityFromToken(cls.normalize(abbreviation))
                if mapped is not None:
                    logger.info(
                        f"role identity resolved from abbreviation: {abbreviation!r} -> {mapped.value}"
                    )
                    return mapped

            # Fall back to role code text when abbreviation does not map directly.
            mapped = cls._identityFromToken(cls.normalize(role.code))
            if mapped is not None:
                logger.info(f"role identity resolved from code: {role.code!r} -> {mapped.value}")
                return mapped

        logger.warning(f"role identity unresolved for candidates: {candidates!r}")
        return None

    @classmethod
    def _identityFromToken(cls, normalizedToken: str) -> RoleIdentity | None:
        """Resolve one identity from a normalized token using generic matching."""

        if not normalizedToken:
            return None

        try:
            return RoleIdentity[normalizedToken.upper()]
        except KeyError:
            pass

        # Some role abbreviations contain modifiers (for example "CFD" or
        # "BPGK"). Map these to the most specific known enum token by prefix
        # or suffix without maintaining a static alias table.
        candidates = sorted(
            (identity for identity in RoleIdentity if identity is not RoleIdentity.UNRESOLVED),
            key=lambda item: len(cls.normalize(item.value)),
            reverse=True,
        )
        for identity in candidates:
            token = cls.normalize(identity.value)
            if not token:
                continue
            if normalizedToken.startswith(token) or normalizedToken.endswith(token):
                return identity

        # Final generic fallback: match enum token characters as an ordered
        # subsequence of the candidate text (for example "goalkeeper" -> "gk").
        for identity in candidates:
            token = cls.normalize(identity.value)
            if not token:
                continue
            if cls._isSubsequence(token, normalizedToken):
                return identity

        return None

    @classmethod
    def _vocabularyLoad(cls) -> TacticVocabulary:
        """Load and cache tactical vocabulary for dynamic role resolution."""

        if cls._vocabulary is None:
            cls._vocabulary = TacticVocabulary()
            tam = cls._vocabulary.roleNormalize("TAM")
            logger.info(
                "loaded role vocabulary: "
                f"roles={len(cls._vocabulary.roles)} TAM={tam.value!r} resolved={tam.resolved}"
            )
        return cls._vocabulary

    @staticmethod
    def _isSubsequence(needle: str, haystack: str) -> bool:
        """Return whether every needle character appears in haystack order."""

        index = 0
        for character in haystack:
            if index < len(needle) and character == needle[index]:
                index += 1
        return index == len(needle)

    @classmethod
    def normalize(cls, value: str) -> str:
        """Normalize role text for robust role vocabulary matching."""

        return "".join(character for character in value if character.isalnum()).casefold()
