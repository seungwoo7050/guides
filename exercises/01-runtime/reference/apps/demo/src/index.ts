// [Implementation 4] 소비자는 workspace package의 exports만 import해 내부 파일 배치와 분리됩니다.
import { parsePort, sum } from "@exercise/math";

console.log("sum", sum([1, 2, 3]));
console.log("port", parsePort(process.env.PORT ?? "4000"));

// [Implementation 5] 등록 순서와 실행 순서를 나란히 두어 sync, microtask, task의 lifecycle 차이를 관찰합니다.
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
