import { describe, expect, it } from "vitest";
import {
  ContractError,
  parseProjectEnvelope,
  parseSearchResult
} from "../lib/catalog-contract";
import type { Project, SearchResult } from "../lib/project-types";

const project: Project = {
  id: "storage-index",
  title: "Storage Index",
  summary: "Validates page and B+ tree changes.",
  status: "active",
  version: 1
};

const result: SearchResult = {
  projects: [project],
  total: 1,
  page: 1,
  pageSize: 4
};

// [Implementation 14-2]
// Runtime contract verification.
describe("runtime catalog contracts", () => {
  it("accepts canonical search and project envelopes", () => {
    expect(parseSearchResult(result)).toEqual(result);
    expect(parseProjectEnvelope({ project })).toEqual({ project });
  });

  it("rejects invalid fields and duplicate project identifiers", () => {
    expect(() => parseSearchResult({ ...result, total: -1 })).toThrow(ContractError);
    expect(() =>
      parseSearchResult({ ...result, projects: [project, { ...project }] })
    ).toThrow(/duplicate/i);
    expect(() =>
      parseProjectEnvelope({ project: { ...project, status: "deleted" } })
    ).toThrow(ContractError);
  });
});
