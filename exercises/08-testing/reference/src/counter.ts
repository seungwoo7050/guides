// [Implementation 1] framework 밖의 순수 transition이 counter invariant와 경계값 behavior를 소유합니다.
export type CounterAction = { type: "increment" } | { type: "decrement" } | { type: "reset" };
export function reduceCounter(value: number, action: CounterAction): number {
  if (action.type === "increment") return value + 1;
  if (action.type === "decrement") return Math.max(0, value - 1);
  return 0;
}
