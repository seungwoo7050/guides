#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from source_manifest import SourceEntry, SourceManifestError, build_manifest, read_entry_text

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
PUNCTUATION_RE = re.compile(r"[^\w\-\s가-힣]", re.UNICODE)


def fail(message: str) -> None:
    raise SystemExit(f"LINK ERROR: {message}")


def markdown_files(entries: tuple[SourceEntry, ...]) -> list[SourceEntry]:
    return [entry for entry in entries if entry.relative.suffix.lower() == ".md"]


def anchors(entry: SourceEntry) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    text = FENCE_RE.sub("", read_entry_text(entry))
    for heading in HEADING_RE.findall(text):
        slug = PUNCTUATION_RE.sub("", heading.strip().lower())
        slug = re.sub(r"\s+", "-", slug)
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        result.add(slug if index == 0 else f"{slug}-{index}")
    return result


def main() -> None:
    try:
        manifest = build_manifest(ROOT)
    except SourceManifestError as error:
        fail(str(error))
    files = markdown_files(manifest)
    by_path = {entry.path: entry for entry in manifest}
    source_directories = {ROOT.resolve()}
    for entry in manifest:
        parent = entry.path.parent
        while parent != ROOT:
            source_directories.add(parent.resolve())
            parent = parent.parent
    checked = 0
    external = 0
    for entry in files:
        path = entry.path
        text = INLINE_CODE_RE.sub("", FENCE_RE.sub("", read_entry_text(entry)))
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            elif " " in target:
                target = target.split(None, 1)[0]
            path_part, separator, fragment = target.partition("#")
            if target.startswith(("http://", "https://", "mailto:", "tel:")):
                external += 1
                continue
            if path_part.startswith("/"):
                fail(f"absolute local link 금지: {path.relative_to(ROOT)} -> {raw_target}")
            resolved = (path if not path_part else path.parent / unquote(path_part)).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"저장소 밖 local link: {path.relative_to(ROOT)} -> {raw_target}")
            if not resolved.exists():
                fail(f"깨진 local link: {path.relative_to(ROOT)} -> {raw_target}")
            if resolved.is_file() and resolved not in by_path:
                fail(f"canonical source manifest 밖 local file link: {path.relative_to(ROOT)} -> {raw_target}")
            if resolved.is_dir() and resolved not in source_directories:
                fail(f"canonical source manifest 밖 local directory link: {path.relative_to(ROOT)} -> {raw_target}")
            if separator and fragment and resolved.is_file() and resolved.suffix == ".md":
                decoded_fragment = unquote(fragment).lower()
                if decoded_fragment not in anchors(by_path[resolved]):
                    fail(f"깨진 heading anchor: {path.relative_to(ROOT)} -> {raw_target}")
            checked += 1
    print(f"MECHANICAL LINKS OK markdown={len(files)} local={checked} external_unchecked={external}")
    print("LINK LIMIT: external availability and rendered prose meaning are not checked")


if __name__ == "__main__":
    main()
