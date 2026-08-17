import { z } from "zod";

const EnvironmentSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65_535).default(4000),
  DATABASE_URL: z.string().url().optional(),
  WEB_ORIGINS: z.string().default("http://localhost:3000"),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace", "silent"]).default("info")
});

// [Implementation 1-1] Parse process input once at the composition boundary and reject an empty browser-origin policy before any listener or database resource starts.
export function loadConfig(environment: NodeJS.ProcessEnv = process.env) {
  const parsed = EnvironmentSchema.parse(environment);
  const allowedOrigins = parsed.WEB_ORIGINS
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  if (allowedOrigins.length === 0) throw new Error("WEB_ORIGINS must contain at least one origin");
  return {
    port: parsed.PORT,
    databaseUrl: parsed.DATABASE_URL,
    allowedOrigins,
    logLevel: parsed.LOG_LEVEL
  };
}
