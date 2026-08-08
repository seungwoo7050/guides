import { updateProject } from "../../../../lib/projects";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const body: unknown = await request.json().catch(() => null);
  if (!isRenameRequest(body)) {
    return Response.json(
      { code: "invalid_request", message: "제목과 버전을 확인해 주세요." },
      { status: 400 }
    );
  }

  const result = updateProject(id, body.title.trim(), body.version);
  if (result.kind === "not_found") {
    return Response.json(
      { code: "not_found", message: "프로젝트를 찾을 수 없습니다." },
      { status: 404 }
    );
  }
  if (result.kind === "conflict") {
    return Response.json(
      {
        code: "version_conflict",
        message: "다른 변경이 먼저 저장되었습니다.",
        project: result.project
      },
      { status: 409 }
    );
  }
  return Response.json({ project: result.project });
}

function isRenameRequest(value: unknown): value is { title: string; version: number } {
  return (
    typeof value === "object" &&
    value !== null &&
    "title" in value &&
    "version" in value &&
    typeof value.title === "string" &&
    value.title.trim().length > 0 &&
    value.title.trim().length <= 80 &&
    typeof value.version === "number" &&
    Number.isSafeInteger(value.version) &&
    value.version >= 0
  );
}
