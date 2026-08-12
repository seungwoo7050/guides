import { z } from "zod";
import { BoardRoleSchema } from "./board";

// [Implementation 2-1]
// browser에서 온 값은 TypeScript type이 아니라 unknown이므로 transport boundary에서 다시 parse합니다.
// server와 client adapter가 이 공개 schema를 공유해 status 이후의 body 모양까지 같은 계약으로 봅니다.
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
