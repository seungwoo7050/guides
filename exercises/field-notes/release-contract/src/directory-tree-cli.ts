import { basename, resolve } from "node:path";
import { digestDirectoryTree } from "./directory-tree.ts";

const inputs = process.argv.slice(2);
if (inputs.length !== 1) {
  console.error(
    "usage: node src/directory-tree-cli.ts <artifact.xcarchive|artifact.app>",
  );
  process.exitCode = 2;
} else {
  const directory = resolve(inputs[0]!);
  try {
    const evidence = await digestDirectoryTree(directory);
    console.log(
      JSON.stringify(
        { directoryName: basename(directory), ...evidence },
        null,
        2,
      ),
    );
    console.error(
      "LIMIT: this records directory path/mode/content identity; signing trust, entitlement correctness, install, and launch remain separate gates",
    );
  } catch (error) {
    console.error(`DIRECTORY TREE ERROR reason=${String(error)}`);
    process.exitCode = 1;
  }
}
