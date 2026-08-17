import assert from "node:assert/strict";
import test from "node:test";
import { searchUsers } from "../lib/fake-api.ts";

test("empty search returns the complete stable directory", async () => {
  const users = await searchUsers("", new AbortController().signal);
  assert.deepEqual(users.map((user) => user.handle), ["alpha", "beta", "gamma"]);
});

test("search normalizes whitespace and casing", async () => {
  const users = await searchUsers("  BETA ", new AbortController().signal);
  assert.deepEqual(users.map((user) => user.handle), ["beta"]);
});

test("the adapter exposes its explicit failure case", async () => {
  await assert.rejects(searchUsers("error", new AbortController().signal), /search failure/i);
});

test("aborting revokes completion of an older request", async () => {
  const controller = new AbortController();
  const pending = searchUsers("a", controller.signal);
  controller.abort();
  await assert.rejects(pending, (error) => error instanceof DOMException && error.name === "AbortError");
});
