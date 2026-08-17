// [Implementation 2] Establish the shared package boundary with a pure operation that has no external state ownership.
export function sum(values: readonly number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

// [Implementation 3] Narrow external input from unknown and return a number only after the TCP port invariant is satisfied.
export function parsePort(input: unknown): number {
  const value = typeof input === "string" ? Number(input) : input;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error("Port must be an integer from 1 through 65535.");
  }
  return value;
}
