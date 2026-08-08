import { parsePort, sum } from "@exercise/math";

console.log("sum", sum([1, 2, 3]));
console.log("port", parsePort(process.env.PORT ?? "4000"));

console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
