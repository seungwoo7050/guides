import type { Project, SearchResult } from "./project-types";

export type CatalogState =
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "pending"; previous: SearchResult }
  | { status: "error"; message: string; previous: SearchResult };

export function createCatalogState(result: SearchResult): CatalogState {
  // TODO(stage-02): 빈 결과와 정상 결과를 다른 상태로 만드세요.
  return { status: "ready", result };
}

export function beginCatalogRequest(state: CatalogState): CatalogState {
  // TODO(stage-02): 마지막으로 확인된 결과를 보존한 pending 상태를 만드세요.
  return state;
}

export function completeCatalogRequest(result: SearchResult): CatalogState {
  // TODO(stage-02): result에 맞는 success 상태를 만드세요.
  return { status: "ready", result };
}

export function failCatalogRequest(state: CatalogState, message: string): CatalogState {
  // TODO(stage-02): 이전 결과를 보존한 error 상태를 만드세요.
  return { status: "error", message, previous: selectCatalogResult(state) };
}

export function selectCatalogResult(state: CatalogState): SearchResult {
  return state.status === "ready" || state.status === "empty"
    ? state.result
    : state.previous;
}

export function replaceProjectInResult(result: SearchResult, project: Project): SearchResult {
  return {
    ...result,
    projects: result.projects.map((candidate) =>
      candidate.id === project.id ? project : candidate
    )
  };
}

export function replaceProjectInCatalogState(
  state: CatalogState,
  project: Project
): CatalogState {
  // TODO(stage-02): 모든 상태 variant에서 마지막 결과의 project를 교체하세요.
  if (state.status === "ready" || state.status === "empty") {
    return { ...state, result: replaceProjectInResult(state.result, project) };
  }
  return state;
}
