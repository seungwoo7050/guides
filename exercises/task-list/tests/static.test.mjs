import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const [html, css, js] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("../style.css", import.meta.url), "utf8"),
  readFile(new URL("../app.js", import.meta.url), "utf8")
]);

test("semantic and accessibility anchors are present", () => {
  assert.match(html, /<html[^>]+lang="en"/i);
  assert.match(html, /class="skip-link"[^>]+href="#main"/);
  assert.match(html, /<main id="main"/);
  assert.match(html, /role="status"/);
  assert.match(html, /role="alert"/);
});

test("user content is projected without innerHTML", () => {
  assert.doesNotMatch(js, /\.innerHTML\s*=/);
  assert.match(js, /title\.textContent = task\.title/);
});

test("state recovery covers storage and history navigation", () => {
  assert.match(js, /localStorage\.setItem/);
  assert.match(js, /JSON\.parse/);
  assert.match(js, /popstate/);
  assert.match(js, /history\.pushState/);
});

test("layout defines narrow viewport and visible focus behavior", () => {
  assert.match(css, /@media \(max-width: 30rem\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /overflow-wrap: anywhere/);
});
