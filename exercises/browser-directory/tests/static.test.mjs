import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const [html, css, js] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("../style.css", import.meta.url), "utf8"),
  readFile(new URL("../app.js", import.meta.url), "utf8")
]);

test("search semantics and accessibility anchors are explicit", () => {
  assert.match(html, /role="search"/);
  assert.match(html, /label for="query"/);
  assert.match(html, /role="status"/);
  assert.match(html, /href="#main"/);
});

test("the URL owns search state", () => {
  assert.match(js, /new URL\(location\.href\)/);
  assert.match(js, /history\.pushState/);
  assert.match(js, /popstate/);
});

test("result data cannot become markup", () => {
  assert.doesNotMatch(js, /\.innerHTML\s*=/);
  assert.match(js, /heading\.textContent = doc\.title/);
  assert.match(js, /body\.textContent = doc\.body/);
});

test("layout handles narrow screens and long content", () => {
  assert.match(css, /@media \(max-width: 32rem\)/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.match(css, /:focus-visible/);
});
