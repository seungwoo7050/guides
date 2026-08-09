import { readFile } from "node:fs/promises";
import { parseAndValidateEasProfileJson } from "./eas-profile-contract.ts";

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error("usage: node src/eas-profile-cli.ts <eas.json> [...]");
  process.exitCode = 2;
} else {
  for (const file of files) {
    try {
      const result = parseAndValidateEasProfileJson(await readFile(file, "utf8"));
      if (!result.ok) {
        console.error(`EAS PROFILE CONTRACT INVALID file=${file}`);
        for (const error of result.errors) console.error(`- ${error}`);
        console.error(`ASSESSMENT ${JSON.stringify(result.assessment)}`);
        process.exitCode = 1;
        continue;
      }
      console.log(`EAS PROFILE CONTRACT OK file=${file}`);
      console.log(`ASSESSMENT ${JSON.stringify(result.assessment)}`);
    } catch {
      console.error(`EAS PROFILE CONTRACT ERROR file=${file} reason=read-failed`);
      process.exitCode = 1;
    }
  }
}
