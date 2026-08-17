import { z } from "zod";

// [Implementation 1] Define the authenticated identity model and normalize every externally supplied authentication or profile payload.
export type Role = "user" | "admin";

export interface User {
  id: string;
  handle: string;
  displayName: string;
  role: Role;
}

export const LoginSchema = z.object({
  handle: z.enum(["alpha", "admin"])
});

export const ProfileSchema = z.object({
  displayName: z.string().trim().min(1).max(40)
});
