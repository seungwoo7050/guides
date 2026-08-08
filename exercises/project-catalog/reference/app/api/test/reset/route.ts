import { restoreProjects } from "../../../../lib/projects";

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
