import assert from "node:assert/strict";
import path from "node:path";
import { access, readFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchBrowser } from "../../../scripts/lib/browser-harness.mjs";

const exercise = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(exercise, "..", "..");
const targetName = process.argv[2] ?? "work";
const target = resolveTarget(targetName);
for (const file of ["index.html", "style.css", "app.js"]) await access(path.join(target, file));
const js = await readFile(path.join(target, "app.js"), "utf8");
assert.doesNotMatch(js, /\.innerHTML\s*=/, "검색 결과는 DOM 노드와 textContent로 렌더링해 주세요.");

const browser = await launchBrowser(pathToFileURL(path.join(target, "index.html")).href, { width: 900, height: 700 });
try {
  const structure = await browser.evaluate(`(() => ({
    main: Boolean(document.querySelector('main#main')),
    nav: document.querySelector('nav')?.getAttribute('aria-label'),
    label: Boolean(document.querySelector('label[for="query"]')),
    button: document.querySelector('button[type="submit"]')?.textContent?.trim(),
    status: document.querySelector('#status')?.getAttribute('role'),
    skip: document.querySelector('.skip-link')?.getAttribute('href')
  }))()`);
  assert.deepEqual(structure, { main: true, nav: "주 메뉴", label: true, button: "검색", status: "status", skip: "#main" });
  assert.equal(await browser.evaluate("document.querySelectorAll('#results article').length"), 4);

  await browser.press("Tab");
  assert.equal(await browser.evaluate("document.activeElement?.classList.contains('skip-link')"), true);

  async function search(query) {
    await browser.evaluate(`(() => {
      const input = document.querySelector('#query');
      input.value = ${JSON.stringify(query)};
      input.dispatchEvent(new Event('input', { bubbles: true }));
      document.querySelector('#search-form').requestSubmit();
    })()`);
  }
  await search("api");
  assert.equal(await browser.evaluate("new URL(location.href).searchParams.get('q')"), "api");
  assert.equal(await browser.evaluate("document.querySelectorAll('#results article').length"), 1);
  assert.match(await browser.evaluate("document.querySelector('#results')?.textContent"), /HTTP API/);

  await search("runtime");
  assert.equal(await browser.evaluate("document.querySelector('#query').value"), "runtime");
  await browser.evaluate("history.back()");
  await browser.waitFor(async () => await browser.evaluate("document.querySelector('#query').value") === "api", 2_000, "검색 상태 복원");
  assert.equal(await browser.evaluate("document.querySelectorAll('#results article').length"), 1);

  await browser.resize(320, 700);
  assert.equal(await browser.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), true, "320px에서 가로 스크롤이 생깁니다.");
  console.log(`${targetName}: 브라우저 UI 계약을 확인했습니다.`);
} finally {
  await browser.close();
}

function resolveTarget(argument) {
  if (path.isAbsolute(argument)) return path.resolve(argument);
  const normalized = path.normalize(argument);
  if (normalized === "exercises" || normalized.startsWith(`exercises${path.sep}`)) {
    return path.resolve(repositoryRoot, normalized);
  }
  return path.resolve(exercise, normalized);
}
