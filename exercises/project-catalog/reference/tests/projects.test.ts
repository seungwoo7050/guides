import { beforeEach, describe, expect, it } from "vitest";
import { GET as searchRoute } from "../app/api/projects/route";
import { PATCH as updateRoute } from "../app/api/projects/[id]/route";
import { restoreProjects, searchProjects, updateProject } from "../lib/projects";

describe("프로젝트 저장소와 HTTP 계약", () => {
  beforeEach(restoreProjects);

  it("검색어, 상태와 페이지 조건을 함께 적용합니다", () => {
    expect(searchProjects({ q: "저장소", status: "active", page: 1 }).projects).toMatchObject([
      { id: "storage-index" }
    ]);
    expect(searchProjects({ q: "", status: "paused", page: 1 }).total).toBe(2);
  });

  it("현재 version만 수정하고 오래된 version에는 최신 값을 반환합니다", () => {
    expect(updateProject("network-inspector", "새 제목", 1)).toMatchObject({
      kind: "updated",
      project: { title: "새 제목", version: 2 }
    });
    expect(updateProject("network-inspector", "뒤늦은 제목", 1)).toMatchObject({
      kind: "conflict",
      project: { title: "새 제목", version: 2 }
    });
  });

  it("검색 Route Handler가 정규화된 결과를 반환합니다", async () => {
    const response = await searchRoute(
      new Request("http://localhost/api/projects?q=%EC%A0%80%EC%9E%A5%EC%86%8C&status=active&page=1")
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      projects: [{ id: "storage-index" }],
      total: 1,
      page: 1
    });
  });

  it("PATCH가 입력 오류, 성공, conflict와 not found를 구분합니다", async () => {
    const invalid = await updateRoute(
      requestBody({ title: "", version: 1 }),
      context("network-inspector")
    );
    expect(invalid.status).toBe(400);

    const updated = await updateRoute(
      requestBody({ title: "새 제목", version: 1 }),
      context("network-inspector")
    );
    expect(updated.status).toBe(200);

    const conflict = await updateRoute(
      requestBody({ title: "뒤늦은 제목", version: 1 }),
      context("network-inspector")
    );
    expect(conflict.status).toBe(409);
    await expect(conflict.json()).resolves.toMatchObject({
      code: "version_conflict",
      project: { title: "새 제목", version: 2 }
    });

    const missing = await updateRoute(
      requestBody({ title: "없음", version: 1 }),
      context("missing")
    );
    expect(missing.status).toBe(404);
  });
});

function requestBody(body: unknown) {
  return new Request("http://localhost/api/projects/id", {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
}

function context(id: string) {
  return { params: Promise.resolve({ id }) };
}
