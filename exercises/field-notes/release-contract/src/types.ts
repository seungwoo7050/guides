export type Platform = "android" | "ios";

export type ArtifactKind =
  | "android-aab"
  | "android-apk"
  | "ios-xcarchive"
  | "ios-ipa"
  | "ios-simulator-app";

export type ArtifactRole =
  | "publishing"
  | "device-installable"
  | "archive"
  | "simulator-installable";

export type ManualCheck =
  | {
      status: "verified";
      method: string;
      observedAt: string;
      evidenceRef: string;
    }
  | {
      status: "not-run";
      reason: string;
      requiredEvidence: string;
    };

export type InstallationCheck =
  | {
      status: "verified";
      deviceClass: "physical" | "emulator" | "simulator";
      deviceIdentityRedacted: string;
      installedApplicationId: string;
      installedVersion: string;
      installedBuildNumber: string;
      observedAt: string;
      evidenceRef: string;
    }
  | {
      status: "not-run";
      reason: string;
      requiredEvidence: string;
    };

export type StoreCheck =
  | {
      status: "uploaded" | "reviewed" | "released";
      track: string;
      observedAt: string;
      evidenceRef: string;
      deliveredArtifactSha256?: string;
    }
  | {
      status: "not-run";
      reason: string;
      requiredEvidence: string;
    };

export type ReleaseEvidence = {
  schemaVersion: 1;
  source: {
    commit: string;
    treeSha256: string;
    packageLockSha256: string;
  };
  application: {
    platform: Platform;
    applicationId: string;
    version: string;
    buildNumber: string;
    runtimeVersion: string;
  };
  build: {
    profile: "development" | "preview" | "production";
    tool: string;
    generatedConfigSha256: string;
    nativeBoundaryReviewRef: string;
  };
  artifact: {
    kind: ArtifactKind;
    fileName: string;
    byteSize: number;
    sha256: string;
  };
  signing: ManualCheck;
  installation: InstallationCheck;
  store: StoreCheck;
  limitations: string[];
};

export type ValidationResult =
  | {
      ok: true;
      evidence: ReleaseEvidence;
      artifactRole: ArtifactRole;
      localArtifactIdentified: true;
      installationVerified: boolean;
      physicalDeviceVerified: boolean;
      storeDeliveredBytesVerified: boolean;
    }
  | { ok: false; errors: string[] };

export type CrossPlatformAssessment = {
  sameSource: boolean;
  androidDeviceVerified: boolean;
  iosDeviceVerified: boolean;
  crossPlatformDeviceVerified: boolean;
  errors: string[];
};
