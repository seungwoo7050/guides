import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// [Implementation 1-2]
// pnpm의 실제 install 위치와 이 app의 공통 조상을 tracing/build root로 사용합니다.
// 이 경계를 잘못 잡으면 독립 worktree나 filter build에서 workspace package가 산출물에서 빠질 수 있습니다.
const appDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectDirectory = path.resolve(appDirectory, "../..");
const nextPackage = createRequire(import.meta.url).resolve("next/package.json");
const nodeModulesSegment = `${path.sep}node_modules${path.sep}`;
const nodeModulesIndex = nextPackage.indexOf(nodeModulesSegment);
const installDirectory = nodeModulesIndex >= 0
  ? nextPackage.slice(0, nodeModulesIndex)
  : projectDirectory;
const workspaceDirectory = commonAncestor(projectDirectory, installDirectory);

export default {
  agentRules: false,
  allowedDevOrigins: ["127.0.0.1"],
  outputFileTracingRoot: workspaceDirectory,
  turbopack: {
    root: workspaceDirectory
  }
};

function commonAncestor(left, right) {
  let candidate = path.resolve(left);
  const target = path.resolve(right);
  while (path.relative(candidate, target).startsWith(`..${path.sep}`) || path.relative(candidate, target) === "..") {
    const parent = path.dirname(candidate);
    if (parent === candidate) return parent;
    candidate = parent;
  }
  return candidate;
}
