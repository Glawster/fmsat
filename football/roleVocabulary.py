"""Shared role vocabulary helpers for parsers and model builders."""

from __future__ import annotations

from fmsat.core.parser import TacticVocabulary
from fmsat.football.roleIdentity import RoleIdentity


class RoleVocabulary:
    """Normalize role text and resolve it to canonical role identities."""

    _vocabulary: TacticVocabulary | None = None

    @classmethod
    def identityResolve(cls, *candidates: str) -> RoleIdentity | None:
        """Resolve one role identity from any number of candidate strings."""

        # Prefer explicit enum-like tokens first (for example "DLP", "WB", "GK").
        for candidate in candidates:
            normalized = cls.normalize(candidate)
            if not normalized:
                continue
            direct = cls._identityFromToken(normalized)
            if direct is not None:
                return direct

        # Then resolve via configured role vocabulary, which includes canonical
        # role codes, display names, aliases, and known abbreviations.
        vocabulary = cls._vocabularyLoad()
        for candidate in candidates:
            normalized = vocabulary.roleNormalize(candidate)
            if not normalized.resolved:
                continue
            role = vocabulary.roles.get(normalized.value)
            if role is None:
                continue
            for abbreviation in role.abbreviations:
                mapped = cls._identityFromToken(cls.normalize(abbreviation))
                if mapped is not None:
                    return mapped

            # Fall back to role code text when abbreviation does not map directly.
            mapped = cls._identityFromToken(cls.normalize(role.code))
            if mapped is not None:
                return mapped

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
