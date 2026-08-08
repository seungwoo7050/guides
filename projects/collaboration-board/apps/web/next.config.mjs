import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

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
