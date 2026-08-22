import { parseProjectQuery } from "../../../lib/catalog-contract";
import { searchProjects } from "../../../lib/projects";

// [Implementation 10]
// Search HTTP boundary.
export async function GET(request: Request) {
  const query = parseProjectQuery(new URL(request.url).searchParams);
  return Response.json(searchProjects(query), {
    headers: { "cache-control": "no-store" }
  });
}
