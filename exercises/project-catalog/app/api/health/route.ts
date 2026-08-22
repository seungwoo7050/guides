// [Implementation 12]
// Production health contract.
// Deployment tooling receives only status and release, with no-store identifying the live process response.
// [Implementation 12-1]
// Framework route type generation.
// Run `npm run typecheck` after routes exist so `next typegen` materializes route types before `tsc` checks them.
export async function GET() {
  return Response.json(
    {
      status: "ok",
      release: process.env.APP_RELEASE ?? "local"
    },
    {
      headers: {
        "cache-control": "no-store"
      }
    }
  );
}
