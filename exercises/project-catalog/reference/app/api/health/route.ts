// [Implementation 6] 배포 도구에는 status와 release만 노출하고 no-store로 실행 중인 process의 health를 식별한다.
// [Implementation 6-1] route가 존재한 뒤 `pnpm typecheck`의 `next typegen`으로 route type을 생성하고 `tsc`로 검증한다.
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
