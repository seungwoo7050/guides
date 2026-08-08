export type RuntimeConfig = {
  port: number;
};

export function readRuntimeConfig(env: NodeJS.ProcessEnv): RuntimeConfig {
  const rawPort = env.PORT ?? "4000";
  const port = Number(rawPort);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`PORT는 1~65535의 정수여야 합니다: ${rawPort}`);
  }
  return { port };
}
