import { z } from "zod";

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
