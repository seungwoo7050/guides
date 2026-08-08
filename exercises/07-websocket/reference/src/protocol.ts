import { z } from "zod";

const boardId = z.string().min(1);
const itemId = z.string().min(1);
export const ClientEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId }),
  z.object({ type: z.literal("cursor.move"), boardId, x: z.number(), y: z.number() }),
  z.object({ type: z.literal("item.create"), boardId, content: z.string(), x: z.number(), y: z.number() }),
  z.object({ type: z.literal("item.update"), boardId, itemId, content: z.string(), baseVersion: z.number().int() }),
  z.object({ type: z.literal("item.move"), boardId, itemId, x: z.number(), y: z.number(), baseVersion: z.number().int(), final: z.boolean() }),
  z.object({ type: z.literal("snapshot.request"), boardId })
]);
export type ClientEvent = z.infer<typeof ClientEventSchema>;

export interface BoardSnapshot {
  boardId: string;
  version: number;
  sequence: number;
  items: Array<{ id: string; content: string; x: number; y: number; version: number }>;
}
export type ServerEvent =
  | { type: "board.snapshot"; snapshot: BoardSnapshot }
  | { type: "board.patch"; patch: { boardId: string; sequence: number; operation: string } }
  | { type: "presence.changed"; boardId: string; members: string[] }
  | { type: "board.closed"; boardId: string; reason: string };
