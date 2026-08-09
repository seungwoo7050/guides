import { readFile } from "node:fs/promises";
import { assessCrossPlatform, validateReleaseEvidence } from "./index.ts";

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error("usage: node src/cli.ts <release-evidence.json> [...]");
  process.exitCode = 2;
} else {
  const valid = [];
  for (const file of files) {
    try {
      const result = validateReleaseEvidence(JSON.parse(await readFile(file, "utf8")));
      if (!result.ok) {
        console.error(`RELEASE EVIDENCE INVALID file=${file}`);
        for (const error of result.errors) console.error(`- ${error}`);
        process.exitCode = 1;
        continue;
      }
      valid.push(result.evidence);
      console.log(
        `RELEASE EVIDENCE OK file=${file} platform=${result.evidence.application.platform} ` +
          `artifact_set_complete=${result.artifactSet.releaseCandidateArtifactSetComplete} ` +
          `install_evidence_consistent=${result.installationEvidenceConsistent} ` +
          `physical_device_evidence_consistent=${result.physicalDeviceEvidenceConsistent} ` +
          `store_delivery_review=${result.storeDeliveryReviewState} ` +
          `signing=${JSON.stringify(result.signingSummary)}`,
      );
    } catch (error) {
      console.error(`RELEASE EVIDENCE ERROR file=${file} reason=${String(error)}`);
      process.exitCode = 1;
    }
  }
  if (files.length === 2 && valid.length === 2) {
    const assessment = assessCrossPlatform(valid[0]!, valid[1]!);
    console.log(`CROSS PLATFORM ${JSON.stringify(assessment)}`);
    if (assessment.errors.length > 0) process.exitCode = 1;
  }
  console.log(
    "LIMIT: schema consistency does not perform native build/signature trust/install/device/store checks, prove credential ownership or store-delivered bytes, or grant stable approval",
  );
}
