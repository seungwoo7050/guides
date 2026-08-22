import { defineConfig } from "vitest/config";

// [Implementation 14]
// Unit verification configuration.
// Browser specifications are owned by Playwright and excluded from the Node test runner.
export default defineConfig({
  test: {
    environment: "node",
    exclude: ["tests/e2e/**", "node_modules/**", ".next/**"]
  }
});
