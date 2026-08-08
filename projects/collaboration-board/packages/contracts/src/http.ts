import { z } from "zod";
import { BoardRoleSchema } from "./board";

export const UserRoleSchema = z.enum(["user", "admin"]);
export const UserStatusSchema = z.enum(["active", "suspended"]);
export const PublicUserSchema = z.object({
  id: z.string().uuid(),
  handle: z.string(),
  displayName: z.string()
});
export const SessionUserSchema = PublicUserSchema.extend({
  role: UserRoleSchema,
  status: UserStatusSchema
});
export const LoginRequestSchema = z.object({
  handle: z.string().trim().min(2).max(24).regex(/^[a-z0-9-]+$/),
  displayName: z.string().trim().min(1).max(40)
});
export const BoardSummarySchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  role: BoardRoleSchema,
  version: z.number().int().nonnegative(),
  closed: z.boolean()
});
export const CreateBoardSchema = z.object({
  title: z.string().trim().min(1).max(80)
});
export const InviteMemberSchema = z.object({
  handle: z.string().trim().min(2).max(24),
  role: z.enum(["editor", "viewer"])
});
export const ChangeMemberRoleSchema = z.object({
  role: z.enum(["editor", "viewer"])
});

export type PublicUser = z.infer<typeof PublicUserSchema>;
export type SessionUser = z.infer<typeof SessionUserSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type BoardSummary = z.infer<typeof BoardSummarySchema>;
