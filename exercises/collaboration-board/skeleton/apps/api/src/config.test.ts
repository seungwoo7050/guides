import assert from "node:assert/strict";
import test from "node:test";
import { readRuntimeConfig } from "./config.js";

test("기본 포트와 명시한 포트를 읽는다", () => {
  assert.deepEqual(readRuntimeConfig({}), { port: 4000 });
  assert.deepEqual(readRuntimeConfig({ PORT: "4312" }), { port: 4312 });
});

test("범위를 벗어난 포트를 시작 전에 거부한다", () => {
  assert.throws(() => readRuntimeConfig({ PORT: "0" }));
  assert.throws(() => readRuntimeConfig({ PORT: "not-a-number" }));
  assert.throws(() => readRuntimeConfig({ PORT: "65536" }));
});
