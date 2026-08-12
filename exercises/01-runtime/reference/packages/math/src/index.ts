// [Implementation 2] 공유 package의 첫 기능은 외부 상태가 없는 순수 연산으로 공개 경계를 확인합니다.
export function sum(values: readonly number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

// [Implementation 3] 외부 입력을 unknown에서 시작해 유효한 TCP port invariant를 만족할 때만 number로 반환합니다.
export function parsePort(input: unknown): number {
  const value = typeof input === "string" ? Number(input) : input;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error("포트는 1부터 65535 사이의 정수여야 합니다.");
  }
  return value;
}
