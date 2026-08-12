import { z } from "zod";

// [Implementation 1] 연결에서 받은 JSON은 runtime schema로 좁히고 server event는 별도 outbound contract로 유지합니다.
const boardId = z.string().min(1);
const itemId = z.string().min(1);
export const ClientEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId }),
  z.object({ type: z.literal("cursor.move"), boardId, x: z.number(), y: z.number() }),
  z.object({ type: z.literal("item.create"), boardId, content: z.string(), x: z.number(), y: z.number() }),
  z.object({ type: z.literal("item.update"), boardId, itemId, content: z.string(), baseVersion: z.number().int() }),
  z.object({ type: z.literal("item.move"), boardId, itemId, x: z.number(), y: z.number(), baseVersion: z.number().int(), final: z.boolean() }),
  z.object({
    type: z.literal("snapshot.request"),
    boardId,
    afterSequence: z.number().int().nonnegative().optional()
  })
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
  | { type: "item.preview"; preview: { boardId: string; itemId: string; x: number; y: number; baseVersion: number } }
  | { type: "presence.changed"; boardId: string; members: string[] }
  | { type: "board.closed"; boardId: string; reason: string };
