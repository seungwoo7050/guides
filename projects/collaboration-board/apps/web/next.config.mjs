import path from "node:path";
import { fileURLToPath } from "node:url";

const appDirectory = path.dirname(fileURLToPath(import.meta.url));

export default {
  allowedDevOrigins: ["127.0.0.1"],
  outputFileTracingRoot: path.resolve(appDirectory, "../..")
};
