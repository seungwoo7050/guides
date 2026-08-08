import { ProjectCatalog } from "./project-catalog";
import { parseProjectQuery } from "../lib/catalog-contract";
import { searchProjects } from "../lib/projects";

export default function Page({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  void searchParams;
  // TODO(stage-01): searchParams를 읽어 같은 query와 첫 결과를 화면에 전달하세요.
  const query = parseProjectQuery(new URLSearchParams());
  return <ProjectCatalog initialQuery={query} initialResult={searchProjects(query)} />;
}
