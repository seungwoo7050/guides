import { parseProjectQuery } from "../../../lib/catalog-contract";
import { searchProjects } from "../../../lib/projects";

export async function GET(request: Request) {
  const query = parseProjectQuery(new URL(request.url).searchParams);
  return Response.json(searchProjects(query), {
    headers: { "cache-control": "no-store" }
  });
}
