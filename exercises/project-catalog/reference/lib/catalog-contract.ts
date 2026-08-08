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
  if (!isRecord(value)) throw new ContractError("프로젝트가 객체가 아닙니다.");

  const id = parseNonEmptyString(value.id, "project.id", 120);
  const title = parseNonEmptyString(value.title, "project.title", 80);
  const summary = parseString(value.summary, "project.summary", 500);
  if (!isProjectStatus(value.status)) {
    throw new ContractError("project.status가 허용된 값이 아닙니다.");
  }
  const version = parseNonNegativeInteger(value.version, "project.version");

  return { id, title, summary, status: value.status, version };
}

export function parseSearchResult(value: unknown): SearchResult {
  if (!isRecord(value)) throw new ContractError("검색 응답이 객체가 아닙니다.");
  if (!Array.isArray(value.projects)) {
    throw new ContractError("검색 응답의 projects가 배열이 아닙니다.");
  }

  const projects = value.projects.map(parseProject);
  const uniqueIds = new Set(projects.map((project) => project.id));
  if (uniqueIds.size !== projects.length) {
    throw new ContractError("검색 응답의 프로젝트 식별자가 중복되었습니다.");
  }

  const total = parseNonNegativeInteger(value.total, "search.total");
  const page = parsePositiveInteger(value.page, "search.page");
  const pageSize = parsePositiveInteger(value.pageSize, "search.pageSize");
  if (total < projects.length) {
    throw new ContractError("search.total이 현재 프로젝트 수보다 작습니다.");
  }

  return { projects, total, page, pageSize };
}

export function parseProjectEnvelope(value: unknown): { project: Project } {
  if (!isRecord(value) || !("project" in value)) {
    throw new ContractError("프로젝트 응답 형식이 올바르지 않습니다.");
  }
  return { project: parseProject(value.project) };
}

function isProjectStatus(value: unknown): value is ProjectStatus {
  return value === "active" || value === "paused";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseString(value: unknown, name: string, maximumLength: number): string {
  if (typeof value !== "string" || value.length > maximumLength) {
    throw new ContractError(`${name}이 문자열 범위를 벗어났습니다.`);
  }
  return value;
}

function parseNonEmptyString(value: unknown, name: string, maximumLength: number): string {
  const parsed = parseString(value, name, maximumLength);
  if (parsed.trim().length === 0) throw new ContractError(`${name}이 비어 있습니다.`);
  return parsed;
}

function parseNonNegativeInteger(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    throw new ContractError(`${name}이 0 이상의 안전한 정수가 아닙니다.`);
  }
  return value;
}

function parsePositiveInteger(value: unknown, name: string): number {
  const parsed = parseNonNegativeInteger(value, name);
  if (parsed === 0) throw new ContractError(`${name}이 양수가 아닙니다.`);
  return parsed;
}
