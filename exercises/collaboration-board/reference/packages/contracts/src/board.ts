import { z } from "zod";

// [Implementation 2]
// HTTP와 WebSocket이 같은 좌표, role, item version을 사용하도록 domain snapshot 계약을 먼저 고정합니다.
// Canvas나 DB adapter는 이 schema를 소비하지만 별도의 정본을 만들지 않습니다.
export const BOARD_WIDTH = 1_600;
export const BOARD_HEIGHT = 900;

export const BoardRoleSchema = z.enum(["owner", "editor", "viewer"]);
export const ItemKindSchema = z.enum(["note", "shape"]);

export const BoardItemSchema = z.object({
  id: z.string().uuid(),
  boardId: z.string().uuid(),
  kind: ItemKindSchema,
  content: z.string().max(2_000),
  x: z.number().finite().min(0).max(BOARD_WIDTH),
  y: z.number().finite().min(0).max(BOARD_HEIGHT),
  width: z.number().finite().min(40).max(800),
  height: z.number().finite().min(40).max(600),
  version: z.number().int().nonnegative()
});

export const BoardSnapshotSchema = z.object({
  boardId: z.string().uuid(),
  title: z.string(),
  version: z.number().int().nonnegative(),
  sequence: z.number().int().nonnegative(),
  closed: z.boolean(),
  role: BoardRoleSchema,
  items: z.array(BoardItemSchema),
  serverTime: z.string().datetime()
});

export type BoardRole = z.infer<typeof BoardRoleSchema>;
export type BoardItem = z.infer<typeof BoardItemSchema>;
export type BoardSnapshot = z.infer<typeof BoardSnapshotSchema>;
