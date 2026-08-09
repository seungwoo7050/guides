export type CounterAction = { type: "increment" } | { type: "decrement" } | { type: "reset" };
export function reduceCounter(value: number, action: CounterAction): number {
  if (action.type === "increment") return value + 1;
  if (action.type === "decrement") return value - 1; // TODO: 0 아래로 내려가지 않게 고쳐 주세요.
  return 0;
}
