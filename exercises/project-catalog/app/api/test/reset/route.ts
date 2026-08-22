import { restoreProjects } from "../../../../lib/projects";

// [Implementation 11]
// Test-only reset boundary.
// Both explicit test mode and an exact token are required so the route is indistinguishable from missing in production.
export async function POST(request: Request) {
  const testMode = process.env.NODE_ENV === "test" || process.env.PLAYWRIGHT === "1";
  const expectedToken = process.env.CATALOG_TEST_RESET_TOKEN;
  const suppliedToken = request.headers.get("x-catalog-test-token");

  if (!testMode || !expectedToken || suppliedToken !== expectedToken) {
    return Response.json({ code: "not_found" }, { status: 404 });
  }

  restoreProjects();
  return Response.json({ ok: true }, { headers: { "cache-control": "no-store" } });
}
