import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const projectRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

describe("완성 workspace", () => {
  it("Stage 01–05 구현 표시가 남아 있지 않습니다", () => {
    const markers = collectMarkers(path.join(projectRoot, "app"))
      .concat(collectMarkers(path.join(projectRoot, "lib")));
    expect(markers).toEqual([]);
  });
});

function collectMarkers(directory: string): string[] {
  const markers: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) markers.push(...collectMarkers(target));
    else if (/\.(?:ts|tsx|css)$/.test(entry.name)) {
      for (const match of readFileSync(target, "utf8").matchAll(/TODO\(stage-0[1-5]\)/g)) {
        markers.push(`${path.relative(projectRoot, target)}:${match[0]}`);
      }
    }
  }
  return markers;
}
