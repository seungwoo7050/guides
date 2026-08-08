import { describe, expect, it } from "vitest";
import {
  ContractError,
  parseProjectEnvelope,
  parseSearchResult
} from "../../lib/catalog-contract";
import {
  beginCatalogRequest,
  completeCatalogRequest,
  createCatalogState,
  failCatalogRequest,
  replaceProjectInCatalogState,
  selectCatalogResult
} from "../../lib/catalog-model";
import type { Project, SearchResult } from "../../lib/project-types";

const project: Project = {
  id: "storage-index",
  title: "저장소 인덱스",
  summary: "페이지와 B+트리를 검증합니다.",
  status: "active",
  version: 1
};

const result: SearchResult = {
  projects: [project],
  total: 1,
  page: 1,
  pageSize: 4
};

describe("Stage 02: runtime contract", () => {
  it("정상 검색 응답을 검증합니다", () => {
    expect(parseSearchResult(result)).toEqual(result);
    expect(parseProjectEnvelope({ project })).toEqual({ project });
  });

  it("잘못된 필드와 중복 식별자를 거절합니다", () => {
    expect(() => parseSearchResult({ ...result, total: -1 })).toThrow(ContractError);
    expect(() =>
      parseSearchResult({ ...result, projects: [project, { ...project }] })
    ).toThrow(/중복/);
    expect(() => parseProjectEnvelope({ project: { ...project, status: "deleted" } })).toThrow(
      ContractError
    );
  });
});

describe("Stage 02: catalog state", () => {
  it("ready·pending·error에서 마지막으로 확인된 결과를 유지합니다", () => {
    const ready = createCatalogState(result);
    const pending = beginCatalogRequest(ready);
    const failed = failCatalogRequest(pending, "실패");
    expect(ready.status).toBe("ready");
    expect(pending.status).toBe("pending");
    expect(failed.status).toBe("error");
    expect(selectCatalogResult(failed)).toEqual(result);
  });

  it("빈 결과와 성공 결과를 서로 다른 상태로 표현합니다", () => {
    expect(completeCatalogRequest({ ...result, projects: [], total: 0 }).status).toBe("empty");
    expect(completeCatalogRequest(result).status).toBe("ready");
  });

  it("현재 화면을 유지하면서 프로젝트 하나를 교체합니다", () => {
    const updated = { ...project, title: "새 제목", version: 2 };
    const pending = beginCatalogRequest(createCatalogState(result));
    const next = replaceProjectInCatalogState(pending, updated);
    expect(next.status).toBe("pending");
    expect(selectCatalogResult(next).projects[0]).toEqual(updated);
  });
});
