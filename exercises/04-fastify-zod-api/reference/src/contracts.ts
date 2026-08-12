import { z } from "zod";
// [Implementation 1] 신뢰하지 않는 HTTP body는 runtime schema가 정규화하고 내부 type은 그 schema에서 파생합니다.
export const CreateMemoSchema = z.object({
  title: z.string().trim().min(1).max(80),
  body: z.string().trim().max(500).default("")
});
export type CreateMemoInput = z.infer<typeof CreateMemoSchema>;
export interface Memo { id: string; title: string; body: string }
