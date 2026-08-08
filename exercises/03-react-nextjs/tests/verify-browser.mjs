import assert from "node:assert/strict";
import { launchBrowser } from "../../../scripts/lib/browser-harness.mjs";

const url = process.argv[2] ?? "http://127.0.0.1:3000";
const browser = await launchBrowser(url, { width: 900, height: 700 });
try {
  assert.match(await browser.evaluate("document.querySelector('h1')?.textContent"), /방문자/);
  await browser.evaluate(`(() => {
    const input = document.querySelector('#name');
    input.value = '  새 이름  ';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  // React's value tracker is updated most reliably through the native setter.
  await browser.evaluate(`(() => {
    const input = document.querySelector('#name');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, '  새 이름  ');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('form').requestSubmit();
  })()`);
  await browser.waitFor(async () => /새 이름/.test(await browser.evaluate("document.querySelector('h1')?.textContent")), 2_000, "이름 변경");

  async function typeQuery(value) {
    await browser.evaluate(`(() => {
      const input = document.querySelector('#query');
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, ${JSON.stringify(value)});
      input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);
  }
  await typeQuery("a");
  await new Promise((resolve) => setTimeout(resolve, 30));
  await typeQuery("beta");
  await browser.waitFor(async () => (await browser.evaluate("document.querySelectorAll('article').length")) === 1, 2_000, "최신 검색 결과");
  assert.match(await browser.evaluate("document.querySelector('article')?.textContent"), /베타/);
  await new Promise((resolve) => setTimeout(resolve, 400));
  assert.equal(await browser.evaluate("document.querySelectorAll('article').length"), 1, "늦은 이전 응답이 최신 결과를 덮었습니다.");
  assert.match(await browser.evaluate("document.querySelector('article')?.textContent"), /베타/);

  await typeQuery("error");
  await browser.waitFor(async () => Boolean(await browser.evaluate("document.querySelector('[role=alert]')?.textContent")), 2_000, "오류 상태");
  assert.match(await browser.evaluate("document.querySelector('[role=alert]')?.textContent"), /검색 실패/);

  await browser.call("Page.navigate", { url: new URL("/profile/alpha", url).href });
  await browser.waitFor(async () => await browser.evaluate("location.pathname === '/profile/alpha' && document.readyState === 'complete'"), 4_000, "동적 경로 직접 접근");
  assert.match(await browser.evaluate("document.body.textContent"), /alpha|알파/i);
  console.log(`React/Next.js 동작 계약을 확인했습니다: ${url}`);
} finally {
  await browser.close();
}
