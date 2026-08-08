export async function GET() {
  // TODO(stage-05): status와 release만 no-store로 반환하세요.
  return Response.json({
    status: "unknown",
    release: "unfinished",
    environment: process.env.NODE_ENV
  });
}
