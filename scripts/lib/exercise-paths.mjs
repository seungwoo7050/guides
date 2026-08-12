import path from "node:path";

export const exerciseSlugs = Object.freeze([
  "00-first-web-app",
  "01-runtime",
  "02-browser",
  "03-react-nextjs",
  "04-fastify-zod-api",
  "05-postgresql-kysely",
  "06-security",
  "07-websocket",
  "08-testing",
  "collaboration-board"
]);

export const learnerWorkspacePaths = Object.freeze(
  exerciseSlugs.map((slug) => path.join("exercises", slug, "work"))
);

export function isLearnerWorkspace(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return learnerWorkspacePaths.includes(relative);
}
