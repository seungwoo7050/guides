export type CounterAction =
  | { type: "increment" }
  | { type: "decrement" }
  | { type: "reset" };

// [Implementation 1] Keep the counter transition outside every framework so its non-negative invariant and reset behavior remain deterministic.
export function reduceCounter(value: number, action: CounterAction): number {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error("counter value must be a non-negative safe integer");
  }
  if (action.type === "increment") {
    if (value === Number.MAX_SAFE_INTEGER) throw new RangeError("counter overflow");
    return value + 1;
  }
  if (action.type === "decrement") return Math.max(0, value - 1);
  return 0;
}
