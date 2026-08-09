import { access, readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const markdown = await collect(root, (file) => file.endsWith(".md"));
const errors = [];
const headingCache = new Map();

for (const file of markdown) {
  const source = await readFile(file, "utf8");
  const visible = stripCodeFences(source);
  const pattern = /\[[^\]]*\]\(([^)]+)\)/g;
  for (const match of visible.matchAll(pattern)) {
    const raw = match[1].trim().replace(/^<|>$/g, "");
    if (!raw || /^(https?:|mailto:|tel:)/.test(raw)) continue;
    const [pathname, hash = ""] = raw.split("#", 2);
    let resolved = file;
    if (pathname) {
      try { resolved = path.resolve(path.dirname(file), decodeURIComponent(pathname)); }
      catch { errors.push(`${relative(file)} -> 잘못된 URL 인코딩: ${raw}`); continue; }
      try { await access(resolved); }
      catch { errors.push(`${relative(file)} -> 존재하지 않음: ${raw}`); continue; }
    }
    if (hash && (await stat(resolved)).isFile() && resolved.endsWith(".md")) {
      const anchors = await headings(resolved);
      const decoded = decodeURIComponent(hash).toLowerCase();
      if (!anchors.has(decoded)) errors.push(`${relative(file)} -> 존재하지 않는 제목: ${raw}`);
    }
  }
}

if (errors.length) {
  console.error("깨진 내부 링크:\n" + errors.join("\n"));
  process.exit(1);
}
console.log(`${markdown.length}개 Markdown 파일의 경로와 제목 링크를 확인했습니다.`);

function stripCodeFences(text) {
  return text.replace(/^```[\s\S]*?^```/gm, "");
}
function slug(text) {
  return text.trim().toLowerCase().replace(/[`*_~]/g, "").replace(/[^\p{L}\p{N}\s-]/gu, "").replace(/\s+/g, "-").replace(/-+/g, "-");
}
async function headings(file) {
  if (headingCache.has(file)) return headingCache.get(file);
  const text = await readFile(file, "utf8");
  const seen = new Map();
  const anchors = new Set();
  for (const match of stripCodeFences(text).matchAll(/^#{1,6}\s+(.+)$/gm)) {
    const base = slug(match[1]);
    const count = seen.get(base) ?? 0;
    anchors.add(count === 0 ? base : `${base}-${count}`);
    seen.set(base, count + 1);
  }
  headingCache.set(file, anchors);
  return anchors;
}
function relative(file) { return path.relative(root, file); }
async function collect(directory, accept) {
  const out = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".git", ".next", ".guide-tmp", "coverage", "dist", "target"].includes(entry.name)) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) out.push(...await collect(full, accept));
    else if (accept(full)) out.push(full);
  }
  return out;
}
