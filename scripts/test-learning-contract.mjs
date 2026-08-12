import assert from "node:assert/strict";

import {
  validateAnnotationEntries,
  validateCollaborationRunnerSource,
  validateIndexRows,
  validateLegacyPathEntries
} from "./verify-learning-contract.mjs";

const marker = (label) => `[${"Implementation"} ${label}]`;
const index = (...labels) => new Map([["00-first-web-app", labels.map((label) => ({ label }))]]);
const regularRows = [{ label: "1", line: "| 1 | source | application logic |" }];
const bootstrapRows = [
  { label: "0", line: "| [Implementation 0] | `pnpm install`, package.json | dependency bootstrap |" },
  ...regularRows
];
const emptyIndexes = () => new Map([
  ["00-first-web-app", regularRows],
  ["01-runtime", bootstrapRows],
  ["02-browser", regularRows],
  ["03-react-nextjs", bootstrapRows],
  ["04-fastify-zod-api", bootstrapRows],
  ["05-postgresql-kysely", bootstrapRows],
  ["06-security", bootstrapRows],
  ["07-websocket", bootstrapRows],
  ["08-testing", bootstrapRows],
  ["collaboration-board", bootstrapRows]
]);

assert.deepEqual(validateIndexRows("01-runtime", [
  { label: "0", line: "| [Implementation 0] | `pnpm install`, package.json | 의존성 bootstrap |" },
  { label: "1", line: "| 1 | source | logic |" },
  { label: "1-1", line: "| 1-1 | source | substep |" },
  { label: "2", line: "| 2 | source | logic |" }
]), []);

expectError(
  validateIndexRows("01-runtime", [
    { label: "0", line: "| [Implementation 0] | `cd`, `mkdir`, `cp` | 일반 파일 복사 |" },
    { label: "1", line: "| 1 | source | logic |" }
  ]),
  /bootstrap 근거|일반 shell\/filesystem/,
  "ordinary shell command is not Implementation zero"
);

expectError(
  validateAnnotationEntries([
    entry("exercises/00-first-web-app/reference/app.js", marker("1")),
    entry("exercises/00-first-web-app/reference/style.css", marker("1"))
  ], index("1")),
  /authoritative anchor가 2개/,
  "duplicate anchor"
);

expectError(
  validateCollaborationRunnerSource('const projectRoot = path.join(root, "projects", "collaboration-board");'),
  /constructed legacy projects 경로/,
  "constructed legacy collaboration runner path"
);
assert.deepEqual(
  validateCollaborationRunnerSource(
    'const projectRoot = path.join(root, "exercises", "collaboration-board", "reference");'
  ),
  []
);

expectError(
  validateIndexRows("gap", [{ label: "1" }, { label: "3" }]),
  /gap 없이/,
  "top-level gap"
);

expectError(
  validateAnnotationEntries([
    entry("exercises/00-first-web-app/skeleton/app.js", marker("1"))
  ], index("1")),
  /둘 수 없는 경로/,
  "forbidden skeleton"
);

expectError(
  validateAnnotationEntries([
    entry("exercises/00-first-web-app/reference.patch", marker("1"))
  ], index("1")),
  /둘 수 없는 경로/,
  "derived patch is not authoritative"
);

expectError(
  validateIndexRows("invalid-zero-child", [{ label: "0-1" }, { label: "1" }]),
  /0-M/,
  "Implementation zero child"
);

expectError(
  validateLegacyPathEntries([
    entry("README.md", `legacy: ${"projects"}/collaboration-board/README.md`)
  ]),
  /legacy collaboration path/,
  "legacy collaboration path"
);

const completeEntries = [];
for (const [scope, rows] of emptyIndexes()) {
  completeEntries.push(entry(
    `exercises/${scope}/README.md`,
    rows.map((row) => marker(row.label)).join("\n")
  ));
}
assert.deepEqual(validateAnnotationEntries(completeEntries, emptyIndexes()), []);

console.log("LEARNING CONTRACT SELF-TEST PASS");

function entry(path, source) {
  return { path, source };
}

function expectError(errors, pattern, label) {
  assert.ok(errors.some((error) => pattern.test(error)), `${label}: 예상 오류가 없습니다.\n${errors.join("\n")}`);
}
