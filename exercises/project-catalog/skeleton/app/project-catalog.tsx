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

  const runSearch = useCallback(async (query: ProjectQuery) => {
    // TODO(stage-03): history 갱신 여부를 분리하고 popstate에서도 이 경로를 사용하세요.
    setCatalog((current) => beginCatalogRequest(current));
    setAnnouncement("검색 결과를 갱신하고 있습니다.");
    const request = coordinator.current.begin();
    try {
      const response = await fetch(`/api/projects?${toProjectSearchParams(query)}`, {
        signal: request.signal
      });
      if (!response.ok) throw new Error("검색 실패");
      const result = parseSearchResult(await response.json());
      // TODO(stage-03): 최신 generation의 결과만 반영하세요.
      setCatalog(completeCatalogRequest(result));
      setAnnouncement(`${result.total}개의 프로젝트를 찾았습니다.`);
    } catch {
      setCatalog((current) =>
        failCatalogRequest(current, "프로젝트를 불러오지 못해 이전 결과를 유지합니다.")
      );
      setAnnouncement("프로젝트를 불러오지 못해 이전 결과를 유지합니다.");
    }
  }, []);

  useEffect(() => {
    // TODO(stage-03): popstate에서 URL을 parse하고 입력·결과를 복원하세요.
    return () => coordinator.current.cancel();
  }, []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = parseProjectQuery(
      toProjectSearchParams({ q: draftQuery, status: draftStatus, page: 1 })
    );
    // TODO(stage-03): 검색 조건을 browser history에 기록하세요.
    await runSearch(query);
  }

  async function rename(project: Project, title: string): Promise<RenameOutcome> {
    const optimistic = { ...project, title };
    setCatalog((current) => replaceProjectInCatalogState(current, optimistic));
    setAnnouncement("변경 내용을 저장하고 있습니다.");
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ title, version: project.version })
      });
      const body = await response.json().catch(() => null);
      // TODO(stage-03): 409는 최신 서버 값과 local draft를 함께 보존하세요.
      if (!response.ok) {
        setCatalog((current) => replaceProjectInCatalogState(current, project));
        const message = "제목을 저장하지 못해 이전 서버 값으로 복구했습니다.";
        setAnnouncement(message);
        return { kind: "error", message };
      }
      const saved = parseProjectEnvelope(body).project;
      setCatalog((current) => replaceProjectInCatalogState(current, saved));
      setAnnouncement("제목을 저장했습니다.");
      return { kind: "success", project: saved };
    } catch {
      setCatalog((current) => replaceProjectInCatalogState(current, project));
      const message = "제목을 저장하지 못해 이전 서버 값으로 복구했습니다.";
      setAnnouncement(message);
      return { kind: "error", message };
    }
  }

  const result = selectCatalogResult(catalog);
  return (
    <main>
      <header className="page-header">
        <p className="eyebrow">Project Catalog</p>
        <h1>프로젝트 목록</h1>
        <p>URL과 서버 버전을 확인하며 프로젝트를 검색하고 수정합니다.</p>
      </header>
      <form className="search" role="search" onSubmit={search}>
        <label htmlFor="query">검색어</label>
        <input
          id="query"
          maxLength={80}
          value={draftQuery}
          onChange={(event) => setDraftQuery(event.target.value)}
        />
        <label htmlFor="status">상태</label>
        <select
          id="status"
          value={draftStatus}
          onChange={(event) =>
            setDraftStatus(event.target.value as ProjectQuery["status"])
          }
        >
          <option value="any">전체</option>
          <option value="active">운영 중</option>
          <option value="paused">중지됨</option>
        </select>
        <button type="submit">검색</button>
      </form>
      <p className="status-message" role="status">{announcement}</p>
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
  const editButton = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);

  function cancel() {
    setDraftTitle(project.title);
    setEditing(false);
    // TODO(stage-04): 조건부 editor가 닫힌 뒤 edit button으로 focus를 복구하세요.
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const outcome = await onRename(project, draftTitle.trim());
    if (outcome.kind === "success") {
      setEditing(false);
      // TODO(stage-04): 저장 성공 뒤 edit button으로 focus를 복구하세요.
    }
  }

  function keyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key === "Escape") cancel();
  }

  return (
    <article aria-label={`${project.title} 프로젝트`}>
      {editing ? (
        <form className="editor" onSubmit={save} onKeyDown={keyDown}>
          <p className="server-value">서버 최신 제목: {project.title}</p>
          <label htmlFor={`title-${project.id}`}>프로젝트 제목</label>
          <input
            ref={input}
            autoFocus
            id={`title-${project.id}`}
            required
            maxLength={80}
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
          />
          <div className="actions">
            <button type="submit">저장</button>
            <button type="button" onClick={cancel}>취소</button>
          </div>
        </form>
      ) : (
        <>
          <div className="title-row">
            <h2>{project.title}</h2>
            <span>{project.status === "active" ? "운영 중" : "중지됨"}</span>
          </div>
          <p>{project.summary}</p>
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
        </>
      )}
    </article>
  );
}
