#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRECTORIES = {".git", ".guide", ".workspace"}
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
REFERENCE_DEFINITION_RE = re.compile(r"^ {0,3}\[([^]\n]*)\]:[ \t]*(.*)$")
INLINE_START_RE = re.compile(r"!?\[([^]\n]*)\]\(")
REFERENCE_USAGE_RE = re.compile(r"!?\[([^]\n]+)\]\[([^]\n]*)\]")
SHORT_REFERENCE_RE = re.compile(r"!?\[([^]\n]+)\]")
ATX_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$")
SETEXT_HEADING_RE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")


@dataclass(frozen=True)
class LinkTarget:
    document: Path
    line: int
    raw_target: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    document: Path
    line: int
    target: str
    message: str

    def render(self, root: Path) -> str:
        location = self.document.relative_to(root).as_posix()
        return f"ERROR [{self.code}] {location}:{self.line}: {self.target!r}: {self.message}"


@dataclass
class CheckResult:
    markdown_files: int = 0
    local_targets_checked: int = 0
    external_targets_excluded: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diagnostics


@dataclass
class DocumentScan:
    targets: list[LinkTarget] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _mask_range(text: str, start: int, end: int) -> str:
    return text[:start] + (" " * (end - start)) + text[end:]


def _mask_inline_code(text: str) -> str:
    characters = list(text)
    cursor = 0
    while cursor < len(text):
        if text[cursor] != "`" or _is_escaped(text, cursor):
            cursor += 1
            continue
        end_of_marker = cursor
        while end_of_marker < len(text) and text[end_of_marker] == "`":
            end_of_marker += 1
        marker = text[cursor:end_of_marker]
        closing = text.find(marker, end_of_marker)
        if closing < 0:
            cursor = end_of_marker
            continue
        for index in range(cursor, closing + len(marker)):
            characters[index] = " "
        cursor = closing + len(marker)
    return "".join(characters)


def _active_lines(text: str) -> list[tuple[int, str, str]]:
    """Return original and comment-masked lines outside fenced code blocks."""

    active: list[tuple[int, str, str]] = []
    fence_character: str | None = None
    fence_length = 0
    in_comment = False

    for line_number, original in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(original)
        if fence_character is not None:
            closing = re.match(
                rf"^ {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*$",
                original,
            )
            if closing:
                fence_character = None
                fence_length = 0
            continue
        if fence:
            marker = fence.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue

        masked = list(original)
        cursor = 0
        while cursor < len(original):
            if in_comment:
                closing = original.find("-->", cursor)
                if closing < 0:
                    for index in range(cursor, len(masked)):
                        masked[index] = " "
                    cursor = len(original)
                else:
                    for index in range(cursor, closing + 3):
                        masked[index] = " "
                    cursor = closing + 3
                    in_comment = False
                continue
            opening = original.find("<!--", cursor)
            if opening < 0:
                break
            closing = original.find("-->", opening + 4)
            if closing < 0:
                for index in range(opening, len(masked)):
                    masked[index] = " "
                in_comment = True
                cursor = len(original)
            else:
                for index in range(opening, closing + 3):
                    masked[index] = " "
                cursor = closing + 3
        active.append((line_number, original, "".join(masked)))
    return active


def _normalize_reference_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).casefold()


def _reference_destination(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value.startswith("<"):
        closing = value.find(">", 1)
        if closing < 0:
            return None
        return value[1:closing]
    match = re.match(r"\S+", value)
    return match.group(0) if match else None


def _find_link_close(text: str, start: int) -> int | None:
    quote: str | None = None
    nested_parentheses = 0
    cursor = start
    while cursor < len(text):
        character = text[cursor]
        if character == "\\":
            cursor += 2
            continue
        if quote is not None:
            if character == quote:
                quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character == "(":
            nested_parentheses += 1
        elif character == ")":
            if nested_parentheses == 0:
                return cursor
            nested_parentheses -= 1
        cursor += 1
    return None


def _inline_destination(text: str, open_parenthesis: int) -> tuple[str, int] | None:
    cursor = open_parenthesis + 1
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text):
        return None
    if text[cursor] == ")":
        return "", cursor

    if text[cursor] == "<":
        closing_angle = text.find(">", cursor + 1)
        if closing_angle < 0:
            return None
        target = text[cursor + 1 : closing_angle]
        closing_link = _find_link_close(text, closing_angle + 1)
        return (target, closing_link) if closing_link is not None else None

    start = cursor
    nested_parentheses = 0
    while cursor < len(text):
        character = text[cursor]
        if character == "\\":
            cursor += 2
            continue
        if character == "(":
            nested_parentheses += 1
        elif character == ")":
            if nested_parentheses == 0:
                return text[start:cursor], cursor
            nested_parentheses -= 1
        elif character.isspace() and nested_parentheses == 0:
            target = text[start:cursor]
            closing_link = _find_link_close(text, cursor)
            return (target, closing_link) if closing_link is not None else None
        cursor += 1
    return None


def _scan_document(document: Path, text: str) -> DocumentScan:
    scan = DocumentScan()
    lines = _active_lines(text)
    definitions: dict[str, LinkTarget] = {}
    definition_lines: set[int] = set()

    for line_number, _original, visible in lines:
        definition = REFERENCE_DEFINITION_RE.match(visible)
        if not definition:
            continue
        definition_lines.add(line_number)
        label = _normalize_reference_label(definition.group(1))
        target = _reference_destination(definition.group(2))
        if not label or target is None:
            scan.diagnostics.append(
                Diagnostic(
                    "E_LINK_REFERENCE",
                    document,
                    line_number,
                    definition.group(0).strip(),
                    "reference definition has no valid label or destination",
                )
            )
            continue
        if label not in definitions:
            occurrence = LinkTarget(document, line_number, target)
            definitions[label] = occurrence
            scan.targets.append(occurrence)

    for line_number, original, visible in lines:
        if line_number in definition_lines:
            continue
        masked = _mask_inline_code(visible)
        cursor = 0
        while True:
            inline = INLINE_START_RE.search(masked, cursor)
            if inline is None:
                break
            if _is_escaped(masked, inline.start()):
                cursor = inline.end()
                continue
            parsed = _inline_destination(original, inline.end() - 1)
            if parsed is None:
                cursor = inline.end()
                continue
            target, closing = parsed
            scan.targets.append(LinkTarget(document, line_number, target))
            masked = _mask_range(masked, inline.start(), closing + 1)
            cursor = closing + 1

        for usage in list(REFERENCE_USAGE_RE.finditer(masked)):
            if _is_escaped(masked, usage.start()):
                continue
            label = usage.group(2) or usage.group(1)
            normalized = _normalize_reference_label(label)
            if normalized not in definitions:
                scan.diagnostics.append(
                    Diagnostic(
                        "E_LINK_REFERENCE",
                        document,
                        line_number,
                        label,
                        "reference usage has no matching definition",
                    )
                )
            masked = _mask_range(masked, usage.start(), usage.end())

        for usage in SHORT_REFERENCE_RE.finditer(masked):
            if _is_escaped(masked, usage.start()):
                continue
            # An undefined shortcut reference is plain Markdown text. A defined
            # shortcut is resolved by the definition target already checked above.
            if _normalize_reference_label(usage.group(1)) in definitions:
                continue
    return scan


def _decode(value: str) -> str | None:
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        return None
    try:
        return unquote(value, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return None


def _heading_text(value: str) -> str:
    value = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"!\[([^]]*)\]\[[^]]*\]", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\[[^]]*\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[`*_~]", "", value)
    return html.unescape(value).strip()


def _base_anchor(heading: str) -> str:
    characters: list[str] = []
    for character in _heading_text(heading).lower():
        category = unicodedata.category(character)
        if character.isspace():
            characters.append(" ")
        elif character in {"-", "_"} or category[0] in {"L", "N"} or category[0] == "M":
            characters.append(character)
    return re.sub(r"\s+", "-", "".join(characters).strip())


def _heading_anchors(path: Path) -> set[str]:
    active = _active_lines(path.read_text(encoding="utf-8"))
    headings: list[str] = []
    for index, (_line_number, _original, visible) in enumerate(active):
        atx = ATX_HEADING_RE.match(visible)
        if atx:
            text = re.sub(r"[ \t]+#+[ \t]*$", "", atx.group(2) or "")
            headings.append(text)
            continue
        if index + 1 < len(active):
            next_line_number, _next_original, next_visible = active[index + 1]
            if next_line_number == active[index][0] + 1 and SETEXT_HEADING_RE.match(next_visible):
                if visible.strip():
                    headings.append(visible.strip())

    anchors: set[str] = set()
    next_suffix: dict[str, int] = {}
    for heading in headings:
        base = _base_anchor(heading)
        candidate = base
        suffix = next_suffix.get(base, 0)
        while candidate in anchors:
            suffix += 1
            candidate = f"{base}-{suffix}"
        next_suffix[base] = suffix
        anchors.add(candidate)
    return anchors


def _local_path(root: Path, document: Path, decoded_path: str) -> tuple[Path | None, str | None]:
    posix_path = PurePosixPath(decoded_path)
    if posix_path.is_absolute():
        return None, "E_LINK_ESCAPE"

    current = document.parent
    for component in posix_path.parts:
        if component in {"", "."}:
            continue
        if component == "..":
            current = current.parent
            if not _is_within(root, current):
                return None, "E_LINK_ESCAPE"
            continue
        current = current / component
        if not _is_within(root, current):
            return None, "E_LINK_ESCAPE"
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            return None, "E_LINK_SYMLINK"
    return current, None


def _validate_target(
    root: Path,
    occurrence: LinkTarget,
    result: CheckResult,
    heading_cache: dict[Path, set[str]],
) -> None:
    raw_target = occurrence.raw_target.strip()
    raw_path, separator, raw_fragment = raw_target.partition("#")
    decoded_path = _decode(raw_path)
    decoded_fragment = _decode(raw_fragment) if separator else ""
    if decoded_path is None or decoded_fragment is None:
        result.diagnostics.append(
            Diagnostic(
                "E_LINK_ESCAPE",
                occurrence.document,
                occurrence.line,
                raw_target,
                "target contains invalid percent-encoded UTF-8",
            )
        )
        return
    if any(character in decoded_path or character in decoded_fragment for character in ("\x00", "\\")):
        result.diagnostics.append(
            Diagnostic(
                "E_LINK_ESCAPE",
                occurrence.document,
                occurrence.line,
                raw_target,
                "NUL and backslash are forbidden in link targets",
            )
        )
        return

    lowered = decoded_path.casefold()
    if lowered.startswith(EXTERNAL_SCHEMES):
        result.external_targets_excluded += 1
        return
    if lowered.startswith("file:") or SCHEME_RE.match(decoded_path):
        result.diagnostics.append(
            Diagnostic(
                "E_LINK_ESCAPE",
                occurrence.document,
                occurrence.line,
                raw_target,
                "absolute and non-approved URL schemes are forbidden",
            )
        )
        return

    result.local_targets_checked += 1
    if decoded_path == "":
        target_path, path_error = occurrence.document, None
    else:
        target_path, path_error = _local_path(root, occurrence.document, decoded_path)
    if path_error is not None:
        message = (
            "link traverses a symbolic-link component"
            if path_error == "E_LINK_SYMLINK"
            else "link path escapes the repository"
        )
        result.diagnostics.append(
            Diagnostic(path_error, occurrence.document, occurrence.line, raw_target, message)
        )
        return
    assert target_path is not None
    if not target_path.exists():
        result.diagnostics.append(
            Diagnostic(
                "E_LINK_MISSING",
                occurrence.document,
                occurrence.line,
                raw_target,
                "local target does not exist",
            )
        )
        return

    if separator and decoded_fragment:
        if not target_path.is_file() or target_path.suffix.casefold() not in {".md", ".markdown"}:
            result.diagnostics.append(
                Diagnostic(
                    "E_LINK_FRAGMENT",
                    occurrence.document,
                    occurrence.line,
                    raw_target,
                    "fragment target is not a Markdown document",
                )
            )
            return
        if target_path not in heading_cache:
            try:
                heading_cache[target_path] = _heading_anchors(target_path)
            except (OSError, UnicodeError):
                heading_cache[target_path] = set()
        anchors = heading_cache[target_path]
        if decoded_fragment not in anchors:
            result.diagnostics.append(
                Diagnostic(
                    "E_LINK_FRAGMENT",
                    occurrence.document,
                    occurrence.line,
                    raw_target,
                    "fragment does not match an actual heading anchor",
                )
            )


def _markdown_files(root: Path) -> list[Path]:
    documents: list[Path] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names if name not in SKIP_DIRECTORIES
        )
        current_path = Path(current)
        for filename in sorted(file_names):
            path = current_path / filename
            if path.suffix.casefold() == ".md" and not path.is_symlink():
                documents.append(path)
    return sorted(documents)


def check_repository(root: Path) -> CheckResult:
    root = root.resolve(strict=True)
    result = CheckResult()
    heading_cache: dict[Path, set[str]] = {}
    documents = _markdown_files(root)
    result.markdown_files = len(documents)
    for document in documents:
        try:
            text = document.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result.diagnostics.append(
                Diagnostic(
                    "E_LINK_MISSING",
                    document,
                    1,
                    document.name,
                    "Markdown document cannot be read as UTF-8",
                )
            )
            continue
        scan = _scan_document(document, text)
        result.diagnostics.extend(scan.diagnostics)
        for target in scan.targets:
            _validate_target(root, target, result, heading_cache)
    result.diagnostics.sort(
        key=lambda item: (
            item.document.relative_to(root).as_posix(),
            item.line,
            item.code,
            item.target,
        )
    )
    return result


def main() -> int:
    result = check_repository(ROOT)
    for diagnostic in result.diagnostics:
        print(diagnostic.render(ROOT), file=sys.stderr)
    scope = (
        f"{result.markdown_files} Markdown files; "
        f"local targets checked={result.local_targets_checked}; "
        f"external targets excluded={result.external_targets_excluded} "
        "(http(s)/mailto not validated; offline manual review required)"
    )
    if not result.ok:
        print(f"link check failed: {scope}", file=sys.stderr)
        return 1
    print(f"links OK (local scope only): {scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
