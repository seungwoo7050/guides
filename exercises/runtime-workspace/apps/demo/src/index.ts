// [Implementation 4] Consume only the workspace package export so the application is decoupled from the library's internal file layout.
import { parsePort, sum } from "@runtime-workspace/math";

console.log("sum", sum([1, 2, 3]));
console.log("port", parsePort(process.env.PORT ?? "4000"));

// [Implementation 5] Place registration and observation together to expose the lifecycle distinction between synchronous work, microtasks, and tasks.
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
