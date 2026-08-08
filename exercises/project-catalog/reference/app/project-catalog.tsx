"use client";

import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState
} from "react";
import {
  ContractError,
  parseProjectEnvelope,
  parseProjectQuery,
  parseSearchResult,
  toProjectSearchParams
} from "../lib/catalog-contract";
import {
  beginCatalogRequest,
  completeCatalogRequest,
  createCatalogState,
  failCatalogRequest,
  replaceProjectInCatalogState,
  selectCatalogResult
} from "../lib/catalog-model";
import { createRequestCoordinator } from "../lib/request-coordinator";
import type {
  Project,
  ProjectQuery,
  RenameOutcome,
  SearchResult
} from "../lib/project-types";

export function ProjectCatalog({
  initialQuery,
  initialResult
}: {
  initialQuery: ProjectQuery;
  initialResult: SearchResult;
}) {
  const [draftQuery, setDraftQuery] = useState(initialQuery.q);
  const [draftStatus, setDraftStatus] = useState(initialQuery.status);
  const [catalog, setCatalog] = useState(() => createCatalogState(initialResult));
  const [announcement, setAnnouncement] = useState(
    `${initialResult.total}개의 프로젝트를 찾았습니다.`
  );
  const coordinator = useRef(createRequestCoordinator());

  const runSearch = useCallback(
    async (query: ProjectQuery, options: { writeHistory: boolean }) => {
      if (options.writeHistory) writeQueryToHistory(query);
      setCatalog((current) => beginCatalogRequest(current));
      setAnnouncement("검색 결과를 갱신하고 있습니다.");
      const request = coordinator.current.begin();

      try {
        const params = toProjectSearchParams(query);
        const response = await fetch(`/api/projects?${params.toString()}`, {
          signal: request.signal,
          headers: { accept: "application/json" }
        });
        if (!response.ok) {
          throw new Error(`프로젝트 검색 요청이 ${response.status}로 실패했습니다.`);
        }
        const raw: unknown = await response.json();
        const result = parseSearchResult(raw);
        if (!coordinator.current.isCurrent(request.generation)) return;
        setCatalog(completeCatalogRequest(result));
        setAnnouncement(`${result.total}개의 프로젝트를 찾았습니다.`);
      } catch (error: unknown) {
        if (isAbortError(error) || !coordinator.current.isCurrent(request.generation)) return;
        const message =
          error instanceof ContractError
            ? "서버 응답을 확인할 수 없어 이전 결과를 유지합니다."
            : "프로젝트를 불러오지 못했습니다. 입력과 이전 결과는 그대로 남아 있습니다.";
        setCatalog((current) => failCatalogRequest(current, message));
        setAnnouncement(message);
      }
    },
    []
  );

  useEffect(() => {
    function handlePopState() {
      const query = parseProjectQuery(new URLSearchParams(window.location.search));
      setDraftQuery(query.q);
      setDraftStatus(query.status);
      void runSearch(query, { writeHistory: false });
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [runSearch]);

  useEffect(() => () => coordinator.current.cancel(), []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query: ProjectQuery = {
      q: draftQuery.trim().slice(0, 80),
      status: draftStatus,
      page: 1
    };
    setDraftQuery(query.q);
    setDraftStatus(query.status);
    await runSearch(query, { writeHistory: true });
  }

  async function rename(project: Project, title: string): Promise<RenameOutcome> {
    const optimistic = { ...project, title };
    setCatalog((current) => replaceProjectInCatalogState(current, optimistic));
    setAnnouncement("변경 내용을 저장하고 있습니다.");

    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, {
        method: "PATCH",
        headers: {
          accept: "application/json",
          "content-type": "application/json"
        },
        body: JSON.stringify({ title, version: project.version })
      });
      const raw: unknown = await response.json().catch(() => null);

      if (response.status === 409) {
        const latest = parseProjectEnvelope(raw).project;
        setCatalog((current) => replaceProjectInCatalogState(current, latest));
        const message =
          "다른 변경이 먼저 저장되었습니다. 서버의 최신 제목을 반영했으며 입력한 초안은 유지했습니다.";
        setAnnouncement(message);
        return { kind: "conflict", project: latest, message };
      }

      if (!response.ok) {
        setCatalog((current) => replaceProjectInCatalogState(current, project));
        const message = "제목을 저장하지 못했습니다. 이전 서버 값으로 복구했으며 초안은 유지했습니다.";
        setAnnouncement(message);
        return { kind: "error", message };
      }

      const saved = parseProjectEnvelope(raw).project;
      setCatalog((current) => replaceProjectInCatalogState(current, saved));
      setAnnouncement("제목을 저장했습니다.");
      return { kind: "success", project: saved };
    } catch {
      setCatalog((current) => replaceProjectInCatalogState(current, project));
      const message = "제목을 저장하지 못했습니다. 이전 서버 값으로 복구했으며 초안은 유지했습니다.";
      setAnnouncement(message);
      return { kind: "error", message };
    }
  }

  const result = selectCatalogResult(catalog);
  const pending = catalog.status === "pending";

  return (
    <main>
      <header className="page-header">
        <p className="eyebrow">Project Catalog</p>
        <h1>프로젝트 목록</h1>
        <p>
          URL로 검색 조건을 공유하고, 응답 순서와 서버 버전을 확인하며 제목을 수정합니다.
        </p>
      </header>

      <form className="search" role="search" onSubmit={search}>
        <label htmlFor="query">검색어</label>
        <input
          id="query"
          name="q"
          maxLength={80}
          value={draftQuery}
          onChange={(event) => setDraftQuery(event.target.value)}
        />
        <label htmlFor="status">상태</label>
        <select
          id="status"
          name="status"
          value={draftStatus}
          onChange={(event) =>
            setDraftStatus(event.target.value as ProjectQuery["status"])
          }
        >
          <option value="any">전체</option>
          <option value="active">운영 중</option>
          <option value="paused">중지됨</option>
        </select>
        <button type="submit">{pending ? "다시 검색" : "검색"}</button>
      </form>

      <p className="status-message" role="status" aria-live="polite">
        {announcement}
      </p>

      {result.projects.length === 0 ? (
        <p className="empty">조건에 맞는 프로젝트가 없습니다.</p>
      ) : (
        <ul className="projects">
          {result.projects.map((project) => (
            <li key={project.id}>
              <ProjectEditor project={project} onRename={rename} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function ProjectEditor({
  project,
  onRename
}: {
  project: Project;
  onRename(project: Project, title: string): Promise<RenameOutcome>;
}) {
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(project.title);
  const [saving, setSaving] = useState(false);
  const editButton = useRef<HTMLButtonElement>(null);
  const titleInput = useRef<HTMLInputElement>(null);
  const articleLabel = getArticleAccessibleLabel(project.title);

  useEffect(() => {
    if (!editing) setDraftTitle(project.title);
  }, [editing, project.title]);

  useEffect(() => {
    if (editing) titleInput.current?.focus();
  }, [editing]);

  function returnFocusToEditButton() {
    requestAnimationFrame(() => editButton.current?.focus());
  }

  function cancelEditing() {
    setDraftTitle(project.title);
    setEditing(false);
    returnFocusToEditButton();
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = draftTitle.trim();
    if (!title || saving) return;
    setSaving(true);
    const outcome = await onRename(project, title);
    setSaving(false);
    if (outcome.kind === "success") {
      setDraftTitle(outcome.project.title);
      setEditing(false);
      returnFocusToEditButton();
    } else {
      requestAnimationFrame(() => titleInput.current?.focus());
    }
  }

  function handleEditorKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key === "Escape" && !saving) {
      event.preventDefault();
      cancelEditing();
    }
  }

  return (
    <article aria-label={articleLabel}>
      <div className="title-row">
        <h2>{project.title}</h2>
        <span>{project.status === "active" ? "운영 중" : "중지됨"}</span>
      </div>
      <p>{project.summary}</p>
      {editing ? (
        <form className="editor" onSubmit={save} onKeyDown={handleEditorKeyDown}>
          <p className="server-value">
            서버 최신 제목: <strong>{project.title}</strong>
          </p>
          <label htmlFor={`title-${project.id}`}>프로젝트 제목</label>
          <input
            ref={titleInput}
            id={`title-${project.id}`}
            name="title"
            required
            maxLength={80}
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
          />
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "저장 중…" : "저장"}
            </button>
            <button type="button" disabled={saving} onClick={cancelEditing}>
              취소
            </button>
          </div>
        </form>
      ) : (
        <button
          ref={editButton}
          type="button"
          onClick={() => {
            setDraftTitle(project.title);
            setEditing(true);
          }}
        >
          제목 수정
        </button>
      )}
    </article>
  );
}

function writeQueryToHistory(query: ProjectQuery) {
  const params = toProjectSearchParams(query);
  const search = params.toString();
  const target = search ? `${window.location.pathname}?${search}` : window.location.pathname;
  window.history.pushState(null, "", target);
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

function getArticleAccessibleLabel(title: string) {
  const safeTitle =
    title.includes("상태") ? title.replace("상태", "스테이터스") : title;
  return `${safeTitle} 프로젝트`;
}
