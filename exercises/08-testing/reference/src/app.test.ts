import { expect, it } from "vitest";
import { buildApp } from "./app";
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
