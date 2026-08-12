"""Markdown reports for inspection, diffs, and parsed tactics."""

from __future__ import annotations

from pathlib import Path

from fmsat.fmf.structures import ChangeGroup, FileInspection, RepeatedStructureCandidate


def inspectionReport(inspection: FileInspection) -> str:
    lines = [
        "File",
        "-----",
        f"Filename: {inspection.path}",
        f"Size: {inspection.size}",
        f"SHA-256: {inspection.sha256}",
        "",
        "Header",
        "------",
        f"Magic: {inspection.header.magicHex}",
        f"ASCII: {inspection.header.magicAscii}",
        f"Version: {inspection.header.version or 'unknown'}",
        f"Flags: {inspection.header.flags or 'unknown'}",
        "",
        "Sections",
        "--------",
    ]
    if inspection.sections:
        lines.extend(
            f"- Offset {item.offset}, length {item.length}, "
            f"confidence {item.confidence:.2f}: {item.reason}"
            for item in inspection.sections[:25]
        )
    else:
        lines.append("- none detected")

    lines.extend(["", "Entropy", "-------", f"Overall entropy: {inspection.entropy:.3f}"])
    lines.extend(
        f"- Offset {item.offset}, length {item.length}, "
        f"entropy {item.entropy:.3f}: {item.classification}"
        for item in inspection.entropyWindows
    )

    successes = [attempt for attempt in inspection.compressionAttempts if attempt.success]
    lines.extend(["", "Compression", "-----------"])
    if successes:
        lines.extend(
            f"- {item.algorithm} at {item.offset}: {item.inputLength} -> {item.outputLength} bytes"
            for item in successes
        )
    else:
        lines.append("- no standard compression succeeded")

    lines.extend(["", "ASCII strings", "-------------"])
    if inspection.strings:
        lines.extend(f"- {item.offset}: {item.value}" for item in inspection.strings[:100])
    else:
        lines.append("- none detected")

    return "\n".join(lines) + "\n"


def diffReport(oldPath: Path, newPath: Path, groups: tuple[ChangeGroup, ...]) -> str:
    lines = [
        "Binary Diff",
        "===========",
        f"Old: {oldPath}",
        f"New: {newPath}",
        "",
        "Grouped changes",
        "---------------",
    ]
    if not groups:
        lines.append("- files are identical")
        return "\n".join(lines) + "\n"
    for group in groups:
        lines.append(
            f"- Offsets {group.start}-{group.end} ({len(group.changes)} changed bytes): "
            f"{group.likelyStructure}"
        )
        for change in group.changes[:32]:
            old = "EOF" if change.old is None else f"0x{change.old:02x}"
            new = "EOF" if change.new is None else f"0x{change.new:02x}"
            lines.append(f"  - {change.offset}: {old} -> {new}")
        if len(group.changes) > 32:
            lines.append(f"  - ... {len(group.changes) - 32} more")
    return "\n".join(lines) + "\n"


def structuresReport(candidates: tuple[RepeatedStructureCandidate, ...]) -> str:
    lines = ["Structure Candidates", "====================", ""]
    if not candidates:
        lines.append("- none detected")
    for candidate in candidates:
        lines.append(
            f"- Offset {candidate.offset}, record length {candidate.recordLength}, "
            f"count {candidate.count}, confidence {candidate.confidence:.2f}: {candidate.reason}"
        )
    return "\n".join(lines) + "\n"
