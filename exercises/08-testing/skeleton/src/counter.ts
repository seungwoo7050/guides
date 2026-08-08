export type CounterAction = { type: "increment" } | { type: "reset" };
export function reduceCounter(value: number, action: CounterAction): number {
  if (action.type === "increment") return value + 1;
  return 0;
}
