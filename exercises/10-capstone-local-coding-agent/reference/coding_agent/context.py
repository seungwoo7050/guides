from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ContractError, PolicyDenied, ReconciliationRequired
from .repository import RepositoryReader
from .types import ContextItem, Grant, RepositorySnapshot, SourceRef
from .util import value_digest


@dataclass(frozen=True)
class KnowledgeDocument:
    source_id: str
    scope: str
    location: str
    revision: str
    trust: str
    freshness: str
    title: str
    content: str
    claims: Mapping[str, str]


@dataclass(frozen=True)
class EvidenceConflict:
    claim: str
    values: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class ContextSelection:
    query: str
    status: str
    items: tuple[ContextItem, ...]
    citations: tuple[str, ...]
    conflicts: tuple[EvidenceConflict, ...] = ()
    stale_sources: tuple[str, ...] = ()
    denied_sources: tuple[str, ...] = ()

    def require_ready(self) -> tuple[ContextItem, ...]:
        if self.status == "READY":
            return self.items
        if self.status == "NO_EVIDENCE":
            raise NoEvidence("no permitted evidence supports the query")
        if self.status == "STALE_EVIDENCE":
            raise StaleEvidence("evidence changed after the recorded revision")
        if self.status == "CONFLICT":
            raise ConflictingEvidence("permitted sources disagree on a material claim")
        raise ContractError(f"unknown context status: {self.status}")


class NoEvidence(ContractError):
    pass


class StaleEvidence(ReconciliationRequired):
    pass


class ConflictingEvidence(ContractError):
    pass


_TOKEN = re.compile(r"[A-Za-z0-9_./-]+|[가-힣]+")


def _text(value: Any, field: str, *, allow_empty: bool = False, maximum: int = 1_000_000) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise ContractError(f"knowledge {field} must be a string")
    if not allow_empty and not value.strip():
        raise ContractError(f"knowledge {field} must not be empty")
    if len(value) > maximum:
        raise ContractError(f"knowledge {field} exceeds {maximum} characters")
    return value


def _knowledge_document(value: Any, source_path: Path) -> KnowledgeDocument:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ContractError(f"knowledge fixture must be an object: {source_path}")
    required = {
        "source_id",
        "scope",
        "revision",
        "trust",
        "freshness",
        "title",
        "content",
        "claims",
    }
    missing = required - set(value)
    extra = set(value) - required
    if missing or extra:
        detail = []
        if missing:
            detail.append("missing " + ", ".join(sorted(missing)))
        if extra:
            detail.append("unknown " + ", ".join(sorted(extra)))
        raise ContractError(f"invalid knowledge fixture {source_path}: {'; '.join(detail)}")
    claims = value["claims"]
    if not isinstance(claims, Mapping) or not all(
        isinstance(key, str) and isinstance(item, str) and key and item for key, item in claims.items()
    ):
        raise ContractError(f"knowledge claims must map non-empty strings: {source_path}")
    freshness = _text(value["freshness"], "freshness", maximum=32).lower()
    if freshness not in {"current", "stale"}:
        raise ContractError(f"knowledge freshness must be current or stale: {source_path}")
    return KnowledgeDocument(
        source_id=_text(value["source_id"], "source_id", maximum=256),
        scope=_text(value["scope"], "scope", maximum=256),
        location=source_path.as_posix(),
        revision=_text(value["revision"], "revision", maximum=256),
        trust=_text(value["trust"], "trust", maximum=64).upper(),
        freshness=freshness,
        title=_text(value["title"], "title", maximum=1000),
        content=_text(value["content"], "content", maximum=1_000_000),
        claims=dict(claims),
    )


def load_knowledge_documents(directory: str | Path) -> tuple[KnowledgeDocument, ...]:
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ContractError(f"knowledge directory is missing: {root}")
    documents: list[KnowledgeDocument] = []
    seen_ids: set[str] = set()
    for path in sorted(root.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError(f"cannot load knowledge fixture: {path}") from error
        document = _knowledge_document(raw, path.relative_to(root))
        if document.source_id in seen_ids:
            raise ContractError(f"duplicate knowledge source_id: {document.source_id}")
        seen_ids.add(document.source_id)
        documents.append(document)
    return tuple(documents)


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"invalid grant expiry: {value}") from error
    if parsed.tzinfo is None:
        raise ContractError("grant expiry must include a timezone")
    return parsed.astimezone(timezone.utc)


def _grant_is_active(grant: Grant, now: datetime) -> None:
    if grant.revoked:
        raise PolicyDenied(f"grant {grant.grant_id} is revoked")
    if _parse_time(grant.expires_at) <= now.astimezone(timezone.utc):
        raise PolicyDenied(f"grant {grant.grant_id} is expired")


def _matches(value: str, patterns: Iterable[str]) -> bool:
    for raw_pattern in patterns:
        pattern = raw_pattern.replace("\\", "/").lstrip("./")
        if pattern in {"", ".", "**", "**/*"}:
            return True
        if pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if value == prefix or value.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def _terms(query: str) -> tuple[str, ...]:
    tokens = tuple(dict.fromkeys(token.casefold() for token in _TOKEN.findall(query) if len(token) > 1))
    return tokens or (query.casefold(),)


def _score(text: str, query: str, terms: tuple[str, ...]) -> int:
    folded = text.casefold()
    score = 10 if query.casefold() in folded else 0
    score += sum(1 for term in terms if term in folded)
    return score


def _excerpt(text: str, terms: tuple[str, ...], *, maximum: int = 1200) -> str:
    lines = text.splitlines() or [text]
    index = next(
        (index for index, line in enumerate(lines) if any(term in line.casefold() for term in terms)),
        0,
    )
    start = max(0, index - 1)
    return "\n".join(lines[start : index + 2])[:maximum]


def _citation(item: ContextItem) -> str:
    reference = item.reference
    return f"[{reference.source_id}] {reference.location}@{reference.revision} {reference.digest}"


def select_context(
    query: str,
    snapshot: RepositorySnapshot,
    grant: Grant,
    *,
    knowledge: Iterable[KnowledgeDocument] = (),
    max_items: int = 12,
    max_characters: int = 12_000,
    now: datetime | None = None,
    principal: str | None = None,
) -> ContextSelection:
    if not isinstance(query, str) or not query.strip() or "\x00" in query:
        raise ContractError("context query must be a non-empty string")
    if max_items <= 0 or max_characters <= 0:
        raise ValueError("context limits must be positive")
    current_time = now or datetime.now(timezone.utc)
    _grant_is_active(grant, current_time)
    if principal is not None and principal != grant.principal:
        raise PolicyDenied(f"grant {grant.grant_id} belongs to a different principal")
    timestamp = current_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    terms = _terms(query)
    reader = RepositoryReader(snapshot)
    candidates: list[tuple[int, ContextItem]] = []
    stale: list[str] = []
    denied: list[str] = []

    for path in sorted(snapshot.files):
        path_score = _score(path, query, terms)
        if not _matches(path, grant.read_paths):
            if path_score:
                denied.append(f"repo:{path}")
            continue
        try:
            read = reader.read_text(path, max_bytes=1_000_000)
        except ReconciliationRequired:
            stale.append(f"repo:{path}")
            continue
        except ContractError:
            continue
        score = max(path_score, _score(read.text, query, terms))
        if score <= 0:
            continue
        excerpt = _excerpt(read.text, terms)
        line = 1
        for index, source_line in enumerate(read.text.splitlines(), start=1):
            if any(term in source_line.casefold() for term in terms):
                line = index
                break
        reference = SourceRef(
            source_id=f"repo:{path}:{line}",
            origin="repository",
            location=f"{path}#L{line}",
            revision=snapshot.snapshot_id,
            digest=read.digest,
            trust="UNTRUSTED",
            scope=path,
            freshness="current",
            retrieved_at=timestamp,
        )
        candidates.append((score, ContextItem(reference=reference, excerpt=excerpt, kind="FACT")))

    relevant_knowledge: list[KnowledgeDocument] = []
    for document in knowledge:
        score = _score(f"{document.title}\n{document.content}", query, terms)
        if score <= 0:
            continue
        source_label = (
            document.source_id if document.source_id.startswith("knowledge:") else f"knowledge:{document.source_id}"
        )
        if not _matches(document.scope, grant.knowledge_scopes):
            denied.append(source_label)
            continue
        relevant_knowledge.append(document)
        if document.freshness != "current":
            stale.append(source_label)
        digest = value_digest(
            {
                "source_id": document.source_id,
                "revision": document.revision,
                "content": document.content,
                "claims": dict(document.claims),
            }
        )
        reference = SourceRef(
            source_id=document.source_id,
            origin="knowledge",
            location=document.location,
            revision=document.revision,
            digest=digest,
            trust=document.trust,
            scope=document.scope,
            freshness=document.freshness,
            retrieved_at=timestamp,
        )
        candidates.append(
            (score, ContextItem(reference=reference, excerpt=_excerpt(document.content, terms), kind="FACT"))
        )

    conflicts: list[EvidenceConflict] = []
    claim_values: dict[str, dict[str, list[str]]] = {}
    for document in relevant_knowledge:
        for claim, value in document.claims.items():
            claim_values.setdefault(claim, {}).setdefault(value, []).append(document.source_id)
    for claim, values in sorted(claim_values.items()):
        if len(values) > 1:
            conflicts.append(
                EvidenceConflict(
                    claim=claim,
                    values={value: tuple(sorted(source_ids)) for value, source_ids in sorted(values.items())},
                )
            )

    candidates.sort(key=lambda pair: (-pair[0], pair[1].reference.source_id))
    selected: list[ContextItem] = []
    character_count = 0
    for _, item in candidates:
        if len(selected) >= max_items:
            break
        if character_count + len(item.excerpt) > max_characters:
            continue
        selected.append(item)
        character_count += len(item.excerpt)

    if stale:
        status = "STALE_EVIDENCE"
    elif conflicts:
        status = "CONFLICT"
    elif selected:
        status = "READY"
    else:
        status = "NO_EVIDENCE"
    return ContextSelection(
        query=query,
        status=status,
        items=tuple(selected),
        citations=tuple(_citation(item) for item in selected),
        conflicts=tuple(conflicts),
        stale_sources=tuple(sorted(set(stale))),
        denied_sources=tuple(sorted(set(denied))),
    )


def build_context(
    query: str,
    snapshot: RepositorySnapshot,
    grant: Grant,
    *,
    knowledge_directory: str | Path | None = None,
    max_items: int = 12,
    max_characters: int = 12_000,
    now: datetime | None = None,
    principal: str | None = None,
) -> ContextSelection:
    knowledge = () if knowledge_directory is None else load_knowledge_documents(knowledge_directory)
    return select_context(
        query,
        snapshot,
        grant,
        knowledge=knowledge,
        max_items=max_items,
        max_characters=max_characters,
        now=now,
        principal=principal,
    )


def render_context(selection: ContextSelection) -> str:
    lines = [f"status: {selection.status}", f"query: {selection.query}"]
    for item, citation in zip(selection.items, selection.citations, strict=True):
        lines.extend(("", citation, item.excerpt))
    if selection.conflicts:
        lines.append("\nconflicts:")
        for conflict in selection.conflicts:
            values = "; ".join(
                f"{value} <- {', '.join(sources)}" for value, sources in conflict.values.items()
            )
            lines.append(f"- {conflict.claim}: {values}")
    if selection.stale_sources:
        lines.append("\nstale: " + ", ".join(selection.stale_sources))
    if selection.denied_sources:
        lines.append("\ndenied: " + ", ".join(selection.denied_sources))
    return "\n".join(lines) + "\n"
