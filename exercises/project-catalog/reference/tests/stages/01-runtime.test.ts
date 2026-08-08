import { describe, expect, it } from "vitest";
import Page from "../../app/page";
import {
  parseProjectQuery,
  toProjectSearchParams,
  toURLSearchParams
} from "../../lib/catalog-contract";

describe("Stage 01: URL과 첫 화면", () => {
  it("잘못된 query를 안전한 기본값으로 정규화합니다", () => {
    const query = parseProjectQuery(
      new URLSearchParams({ q: `  ${"가".repeat(90)}  `, status: "deleted", page: "-4" })
    );
    expect(query).toEqual({ q: "가".repeat(80), status: "any", page: 1 });
    expect(parseProjectQuery(toProjectSearchParams(query))).toEqual(query);
  });

  it("배열 query를 server 입력으로 사용하지 않습니다", () => {
    const params = toURLSearchParams({ q: ["첫째", "둘째"], status: "active", page: "2" });
    expect(params.get("q")).toBeNull();
    expect(params.get("status")).toBe("active");
    expect(params.get("page")).toBe("2");
  });

  it("page가 searchParams와 같은 query·result를 첫 화면에 전달합니다", async () => {
    const element = await Page({
      searchParams: Promise.resolve({ q: "저장소", status: "active", page: "1" })
    });
    expect(element.props.initialQuery).toEqual({ q: "저장소", status: "active", page: 1 });
    expect(element.props.initialResult.projects.map((project: { id: string }) => project.id)).toEqual([
      "storage-index"
    ]);
  });
});
