import { describe, expect, it } from "vitest";

import { createMemoryRepository, RepositoryError } from "./repository";

describe("MemoryRepository", () => {
  it("enforces membership, sequence, optimistic versions, and read-only roles", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const owner = await repo.upsertUser({ handle: "owner", displayName: "Owner" });
    const viewer = await repo.upsertUser({ handle: "viewer", displayName: "Viewer" });
    const board = (await repo.listBoards(owner.id))[0]!;
    const created = await repo.createItem(board.id, owner.id, { kind: "note", content: "one", x: 20, y: 30 });
    expect(created.sequence).toBeGreaterThan(0);
    expect(await repo.updateItem(board.id, owner.id, created.item.id, "two", created.item.version)).toMatchObject({
      item: { content: "two", version: created.item.version + 1 }
    });
    expect(await repo.updateItem(board.id, owner.id, created.item.id, "stale", created.item.version)).toBeNull();
    await expect(repo.createItem(board.id, viewer.id, { kind: "note", content: "blocked", x: 0, y: 0 }))
      .rejects.toMatchObject<Partial<RepositoryError>>({ code: "read_only" });
  });

  it("revokes active sessions when an administrator suspends a user", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const admin = await repo.upsertUser({ handle: "admin", displayName: "Admin" });
    const editor = await repo.upsertUser({ handle: "editor", displayName: "Editor" });
    const token = await repo.createSession(editor.id);
    expect(await repo.getSessionUser(token)).not.toBeNull();
    await repo.setUserStatus(admin.id, editor.id, "suspended", "policy violation");
    expect(await repo.getSessionUser(token)).toBeNull();
  });

  it("protects owner membership, event history, and one-way board closure", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const owner = await repo.upsertUser({ handle: "owner", displayName: "Owner" });
    const board = (await repo.listBoards(owner.id))[0]!;

    await expect(repo.inviteMember(board.id, owner.id, owner.handle, "viewer"))
      .rejects.toMatchObject<Partial<RepositoryError>>({ code: "forbidden" });
    await expect(repo.changeMemberRole(board.id, owner.id, owner.id, "editor"))
      .rejects.toMatchObject<Partial<RepositoryError>>({ code: "forbidden" });

    const events = await repo.listBoardEvents(board.id, owner.id);
    const created = events.find((event) => event.eventType === "item.create")!;
    (created.payload as { content: string }).content = "mutated projection";
    expect((await repo.listBoardEvents(board.id, owner.id)).find((event) => event.id === created.id)?.payload)
      .toMatchObject({ content: "First hypothesis" });

    await repo.closeBoard(board.id, owner.id);
    await expect(repo.closeBoard(board.id, owner.id))
      .rejects.toMatchObject<Partial<RepositoryError>>({ code: "board_closed" });
  });
});
