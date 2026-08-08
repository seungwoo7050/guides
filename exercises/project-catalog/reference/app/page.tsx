import React from "react";
import { ProjectCatalog } from "./project-catalog";
import {
  parseProjectQuery,
  toURLSearchParams
} from "../lib/catalog-contract";
import { searchProjects } from "../lib/projects";

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
