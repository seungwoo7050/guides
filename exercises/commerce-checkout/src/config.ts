import { z } from "zod";

// [Implementation 1] Parse process configuration once before allocating database, provider, or listener resources, and reject incomplete trust boundaries.
const ConfigSchema = z.object({
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().int().min(1).max(65535).default(3001),
  PAYMENT_PROVIDER_URL: z.string().url(),
  PAYMENT_PROVIDER_TIMEOUT_MS: z.coerce.number().int().min(100).max(30_000).default(2_000),
  WEBHOOK_SECRET: z.string().min(16),
  WEBHOOK_TOLERANCE_SECONDS: z.coerce.number().int().min(30).max(3_600).default(300)
});

export type AppConfig = z.infer<typeof ConfigSchema>;

export function loadConfig(env: NodeJS.ProcessEnv): AppConfig {
  return ConfigSchema.parse(env);
}
