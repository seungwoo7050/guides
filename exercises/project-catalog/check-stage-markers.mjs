import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const [targetRoot, rawStage] = process.argv.slice(2);
if (!targetRoot || !/^0[1-5]$/.test(rawStage ?? "")) {
  console.error("사용법: node check-stage-markers.mjs <project-root> <01..05>");
  process.exit(2);
}

const completionStage = Number(rawStage);
const markers = [];
await visit(path.resolve(targetRoot));

const blocking = markers.filter((marker) => marker.stage <= completionStage);
if (blocking.length > 0) {
  console.error(`Stage ${rawStage}까지 구현하지 않은 표시가 남아 있습니다.`);
  for (const marker of blocking) {
    console.error(`- ${path.relative(process.cwd(), marker.file)}:${marker.line} ${marker.text}`);
  }
  process.exit(1);
}

console.log(`Stage ${rawStage}까지의 구현 표시가 모두 제거되었습니다.`);

async function visit(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(entry.name)) {
      continue;
    }
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await visit(target);
      continue;
    }
    if (!/\.(?:ts|tsx|js|mjs|css|md)$/.test(entry.name)) continue;
    const lines = (await readFile(target, "utf8")).split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      for (const match of lines[index].matchAll(/TODO\(stage-(0[1-5])\)/g)) {
        markers.push({
          file: target,
          line: index + 1,
          stage: Number(match[1]),
          text: match[0]
        });
      }
    }
  }
}
