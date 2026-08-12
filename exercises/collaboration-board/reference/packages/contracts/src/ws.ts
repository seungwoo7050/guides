import { z } from "zod";
import { BoardItemSchema, BoardSnapshotSchema, ItemKindSchema } from "./board";

const boardId = z.string().uuid();
const itemId = z.string().uuid();
const coordinate = z.number().finite();

// [Implementation 2-2]
// 오래 유지되는 socket은 join 전후와 transient/final 변경을 구분해야 합니다.
// version은 충돌 판정, sequence는 patch gap 발견과 snapshot 복구의 기준입니다.
export const ClientEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId }),
  z.object({ type: z.literal("cursor.move"), boardId, x: coordinate, y: coordinate }),
  z.object({
    type: z.literal("item.create"),
    boardId,
    kind: ItemKindSchema,
    content: z.string().max(2_000),
    x: coordinate,
    y: coordinate
  }),
  z.object({
    type: z.literal("item.update"),
    boardId,
    itemId,
    content: z.string().max(2_000),
    baseVersion: z.number().int().nonnegative()
  }),
  z.object({
    type: z.literal("item.move"),
    boardId,
    itemId,
    x: coordinate,
    y: coordinate,
    baseVersion: z.number().int().nonnegative(),
    final: z.boolean()
  }),
  z.object({ type: z.literal("snapshot.request"), boardId })
]);

export const BoardPatchSchema = z.object({
  boardId,
  sequence: z.number().int().positive(),
  version: z.number().int().nonnegative(),
  operation: z.enum(["cursor", "item.create", "item.update", "item.move"]),
  actorId: z.string().uuid(),
  item: BoardItemSchema.optional(),
  cursor: z.object({ x: coordinate, y: coordinate }).optional(),
  final: z.boolean().optional()
});

export const ServerEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.snapshot"), snapshot: BoardSnapshotSchema }),
  z.object({ type: z.literal("board.patch"), patch: BoardPatchSchema }),
  z.object({
    type: z.literal("presence.changed"),
    boardId,
    members: z.array(z.object({
      userId: z.string().uuid(),
      displayName: z.string(),
      connected: z.boolean(),
      cursor: z.object({ x: coordinate, y: coordinate }).nullable()
    }))
  }),
  z.object({ type: z.literal("board.closed"), boardId, reason: z.string() })
]);

export type ClientEvent = z.infer<typeof ClientEventSchema>;
export type ServerEvent = z.infer<typeof ServerEventSchema>;
export type BoardPatch = z.infer<typeof BoardPatchSchema>;
