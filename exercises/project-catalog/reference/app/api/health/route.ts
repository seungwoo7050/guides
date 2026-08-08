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
