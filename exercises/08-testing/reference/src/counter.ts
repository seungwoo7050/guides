export type CounterAction = { type: "increment" } | { type: "decrement" } | { type: "reset" };
export function reduceCounter(value: number, action: CounterAction): number {
  if (action.type === "increment") return value + 1;
  if (action.type === "decrement") return Math.max(0, value - 1);
  return 0;
}
