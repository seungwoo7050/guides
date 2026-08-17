import { z } from "zod";

import {
  BOARD_HEIGHT,
  BOARD_WIDTH,
  BoardItemSchema,
  BoardSnapshotSchema,
  ItemKindSchema
} from "./board";

const boardId = z.string().uuid();
const itemId = z.string().uuid();
const xCoordinate = z.number().finite().min(0).max(BOARD_WIDTH);
const yCoordinate = z.number().finite().min(0).max(BOARD_HEIGHT);

// [Implementation 2-2] Distinguish join, transient motion, persistent mutation, version conflict, and sequence recovery in one long-lived socket contract.
export const ClientEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId }),
  z.object({ type: z.literal("cursor.move"), boardId, x: xCoordinate, y: yCoordinate }),
  z.object({
    type: z.literal("item.create"),
    boardId,
    kind: ItemKindSchema,
    content: z.string().max(2_000),
    x: xCoordinate,
    y: yCoordinate
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
    x: xCoordinate,
    y: yCoordinate,
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
  cursor: z.object({ x: xCoordinate, y: yCoordinate }).optional(),
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
      cursor: z.object({ x: xCoordinate, y: yCoordinate }).nullable()
    }))
  }),
  z.object({ type: z.literal("board.closed"), boardId, reason: z.string() })
]);

export type ClientEvent = z.infer<typeof ClientEventSchema>;
export type ServerEvent = z.infer<typeof ServerEventSchema>;
export type BoardPatch = z.infer<typeof BoardPatchSchema>;
