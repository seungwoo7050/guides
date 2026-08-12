import React from "react";
import { ProjectCatalog } from "./project-catalog";
import {
  parseProjectQuery,
  toURLSearchParams
} from "../lib/catalog-contract";
import { searchProjects } from "../lib/projects";

// [Implementation 3] Server Component가 URL query와 첫 결과를 같은 snapshot에서 만들고 직렬화 가능한 props만 client에 넘긴다.
export default async function Page({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = parseProjectQuery(toURLSearchParams(raw));
  const initialResult = searchProjects(query);

  return <ProjectCatalog initialQuery={query} initialResult={initialResult} />;
}
