import type { Project, ProjectQuery, ProjectStatus, SearchResult } from "./project-types";

export class ContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ContractError";
  }
}

export function toURLSearchParams(
  raw: Record<string, string | string[] | undefined>
): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "string") params.set(key, value);
  }
  return params;
}

export function parseProjectQuery(params: URLSearchParams): ProjectQuery {
  const q = (params.get("q") ?? "").trim().slice(0, 80);
  const rawStatus = params.get("status");
  const status: ProjectQuery["status"] = isProjectStatus(rawStatus) ? rawStatus : "any";
  const rawPage = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  return { q, status, page };
}

export function toProjectSearchParams(query: ProjectQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q.length > 0) params.set("q", query.q);
  if (query.status !== "any") params.set("status", query.status);
  if (query.page !== 1) params.set("page", String(query.page));
  return params;
}

export function parseProject(value: unknown): Project {
  // TODO(stage-02): unknown project의 모든 필드와 허용 범위를 검사하세요.
  return value as Project;
}

export function parseSearchResult(value: unknown): SearchResult {
  // TODO(stage-02): 검색 응답, 정수 범위와 중복 id를 검사하세요.
  return value as SearchResult;
}

export function parseProjectEnvelope(value: unknown): { project: Project } {
  // TODO(stage-02): update envelope를 검사하세요.
  return value as { project: Project };
}

function isProjectStatus(value: unknown): value is ProjectStatus {
  return value === "active" || value === "paused";
}
