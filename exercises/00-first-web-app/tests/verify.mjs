import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { access, readFile } from "node:fs/promises";
import { launchBrowser } from "../../../scripts/lib/browser-harness.mjs";

const exercise = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(exercise, "..", "..");
const targetName = process.argv[2] ?? "work";
const target = resolveTarget(targetName);
for (const file of ["index.html", "style.css", "app.js"]) await access(path.join(target, file));

const html = await readFile(path.join(target, "index.html"), "utf8");
const js = await readFile(path.join(target, "app.js"), "utf8");
assert.doesNotMatch(js, /\.innerHTML\s*=/, "사용자 입력을 innerHTML에 넣지 마세요.");
assert.match(html, /<html[^>]+lang=["']ko["']/i, "문서 언어를 선언해 주세요.");

const browser = await launchBrowser(pathToFileURL(path.join(target, "index.html")).href, { width: 900, height: 700 });
try {
  const structure = await browser.evaluate(`(() => ({
    main: Boolean(document.querySelector('main#main')),
    heading: document.querySelector('h1')?.textContent?.trim(),
    label: Boolean(document.querySelector('label[for="task-title"]')),
    form: Boolean(document.querySelector('form#task-form')),
    status: document.querySelector('#status')?.getAttribute('role'),
    alert: document.querySelector('#error')?.getAttribute('role'),
    list: Boolean(document.querySelector('ul#task-list')),
    skip: document.querySelector('.skip-link')?.getAttribute('href')
  }))()`);
  assert.deepEqual(structure, {
    main: true,
    heading: "나의 작업 목록",
    label: true,
    form: true,
    status: "status",
    alert: "alert",
    list: true,
    skip: "#main"
  });

  await browser.press("Tab");
  assert.equal(await browser.evaluate("document.activeElement?.classList.contains('skip-link')"), true, "첫 Tab에서 본문 건너뛰기 링크가 보여야 합니다.");

  await browser.evaluate(`(() => {
    const input = document.querySelector('#task-title');
    input.value = '  첫 작업  ';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('#task-form').requestSubmit();
  })()`);
  await browser.waitFor(async () => await browser.evaluate("document.querySelectorAll('#task-list li').length") === 1, 2_000, "작업 추가");
  assert.equal(await browser.evaluate("document.querySelector('#task-list li span')?.textContent"), "첫 작업");
  assert.match(await browser.evaluate("document.querySelector('#status')?.textContent"), /전체 1개, 미완료 1개/);

  await browser.evaluate(`(() => {
    const input = document.querySelector('#task-title');
    input.value = '   ';
    document.querySelector('#task-form').requestSubmit();
  })()`);
  assert.match(await browser.evaluate("document.querySelector('#error')?.textContent"), /입력/);
  assert.equal(await browser.evaluate("document.querySelectorAll('#task-list li').length"), 1);

  await browser.evaluate(`(() => {
    const checkbox = document.querySelector('#task-list input[type="checkbox"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  await browser.waitFor(async () => await browser.evaluate("document.querySelector('#task-list li')?.dataset.completed") === "true", 2_000, "완료 상태");

  await browser.evaluate(`(() => {
    const select = document.querySelector('#filter');
    select.value = 'open';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  assert.equal(await browser.evaluate("new URL(location.href).searchParams.get('filter')"), "open");
  assert.equal(await browser.evaluate("document.querySelectorAll('#task-list li').length"), 0);

  await browser.evaluate(`(() => {
    const select = document.querySelector('#filter');
    select.value = 'done';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  assert.equal(await browser.evaluate("document.querySelectorAll('#task-list li').length"), 1);
  await browser.evaluate("history.back()");
  await browser.waitFor(async () => await browser.evaluate("document.querySelector('#filter')?.value") === "open", 2_000, "뒤로 가기 필터 복원");

  await browser.call("Page.reload", { ignoreCache: true });
  await browser.waitFor(async () => await browser.evaluate("document.readyState") === "complete", 4_000, "새로 고침");
  assert.match(await browser.evaluate("document.querySelector('#status')?.textContent"), /전체 1개/);

  await browser.resize(320, 700);
  assert.equal(await browser.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), true, "320px에서 가로 스크롤이 생깁니다.");
  console.log(`${targetName}: 첫 웹 애플리케이션 계약을 확인했습니다.`);
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
