import type { Project, ProjectQuery, SearchResult } from "./project-types";

const PAGE_SIZE = 4;
const initialProjects: Project[] = [
  {
    id: "network-inspector",
    title: "네트워크 흐름 분석",
    summary: "패킷과 연결 상태를 함께 추적합니다.",
    status: "active",
    version: 1
  },
  {
    id: "storage-index",
    title: "저장소 인덱스",
    summary: "페이지와 B+트리의 변경을 검증합니다.",
    status: "active",
    version: 1
  },
  {
    id: "release-monitor",
    title: "배포 상태 추적",
    summary: "배포 결과와 복구 조건을 기록합니다.",
    status: "paused",
    version: 1
  },
  {
    id: "task-runner",
    title: "명령 실행기",
    summary: "시간 제한과 결과 보고서를 관리합니다.",
    status: "active",
    version: 1
  },
  {
    id: "event-recovery",
    title: "이벤트 복구",
    summary: "중복과 순서 역전을 수렴시킵니다.",
    status: "paused",
    version: 1
  }
];

declare global {
  var __guideProjectCatalogStore: Map<string, Project> | undefined;
}

const projects =
  globalThis.__guideProjectCatalogStore ??
  (globalThis.__guideProjectCatalogStore = createInitialStore());

export function searchProjects(query: ProjectQuery): SearchResult {
  const normalized = query.q.toLocaleLowerCase("ko");
  const matches = [...projects.values()].filter((project) => {
    const textMatches =
      normalized.length === 0 ||
      `${project.title} ${project.summary}`.toLocaleLowerCase("ko").includes(normalized);
    const statusMatches = query.status === "any" || project.status === query.status;
    return textMatches && statusMatches;
  });
  const start = (query.page - 1) * PAGE_SIZE;
  return {
    projects: matches.slice(start, start + PAGE_SIZE).map(cloneProject),
    total: matches.length,
    page: query.page,
    pageSize: PAGE_SIZE
  };
}

export function updateProject(id: string, title: string, version: number) {
  const current = projects.get(id);
  if (!current) return { kind: "not_found" as const };
  if (current.version !== version) {
    return { kind: "conflict" as const, project: cloneProject(current) };
  }

  const next: Project = {
    ...current,
    title,
    version: current.version + 1
  };
  projects.set(id, next);
  return { kind: "updated" as const, project: cloneProject(next) };
}

export function restoreProjects() {
  projects.clear();
  for (const project of initialProjects) projects.set(project.id, cloneProject(project));
}

function createInitialStore() {
  return new Map(initialProjects.map((project) => [project.id, cloneProject(project)]));
}

function cloneProject(project: Project): Project {
  return { ...project };
}
