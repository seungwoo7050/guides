import { createApplication } from "./app.js";
import { readRuntimeConfig } from "./config.js";

const config = readRuntimeConfig(process.env);
const application = createApplication();

const stop = async () => {
  await application.close();
};
process.once("SIGINT", stop);
process.once("SIGTERM", stop);

await application.app.listen({ host: "0.0.0.0", port: config.port });
