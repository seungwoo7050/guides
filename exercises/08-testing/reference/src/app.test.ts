import { expect, it } from "vitest";
import { buildApp } from "./app";
// [Implementation 4] app.inject 검사는 실제 route와 serialization을 지나며 각 case가 만든 app resource를 닫습니다.
it("increments through HTTP", async () => {
  const app = buildApp();
  await app.ready();
  const response = await app.inject({ method: "POST", url: "/counter/increment" });
  expect(response.json()).toEqual({ value: 1 });
  await app.close();
});
it("does not decrement below zero through HTTP", async () => {
  const app = buildApp();
  await app.ready();
  const response = await app.inject({ method: "POST", url: "/counter/decrement" });
  expect(response.json()).toEqual({ value: 0 });
  await app.close();
});
