export type Platform = "android" | "ios";

export type DeviceClass = "physical" | "emulator" | "simulator";

export type FileArtifactKind =
  | "android-aab"
  | "android-apk"
  | "ios-xcarchive"
  | "ios-ipa"
  | "ios-simulator-app";

export type StoreArtifactKind =
  | "android-play-split-set"
  | "ios-testflight-build";

export type ArtifactKind = FileArtifactKind | StoreArtifactKind;

export type ArtifactRole =
  | "publishing"
  | "device-installable"
  | "archive"
  | "simulator-installable";

export type FileArtifactEvidence = {
  ref: string;
  kind: FileArtifactKind;
  identity: "local-bytes";
  fileName: string;
  byteSize: number;
  sha256: string;
};

export type StoreArtifactEvidence = {
  ref: string;
  kind: StoreArtifactKind;
  identity: "store-build";
  storeBuildRef: string;
  displayName: string;
};

export type ArtifactEvidence = FileArtifactEvidence | StoreArtifactEvidence;

export type NotRunCheck = {
  status: "not-run";
  reason: string;
  requiredEvidence: string;
};

export type SigningCheck =
  | (NotRunCheck & { artifactRef: string })
  | {
      status: "claimed";
      artifactRef: string;
      redactedIdentity: string;
      method: string;
      observedAt: string;
      evidenceRef: string;
    }
  | {
      status: "manually-reviewed";
      artifactRef: string;
      redactedIdentity: string;
      method: string;
      observedAt: string;
      evidenceRef: string;
      reviewer: string;
      reviewedAt: string;
      reviewEvidenceRef: string;
    };

export type InstallationCheck =
  | NotRunCheck
  | {
      status: "verified";
      artifactRef: string;
      deviceClass: DeviceClass;
      deviceIdentityRedacted: string;
      installedApplicationId: string;
      installedVersion: string;
      installedBuildNumber: string;
      observedRuntimeVersion: string;
      observedRuntimeFingerprintOrPolicy: string;
      launchResult: "passed";
      observedAt: string;
      evidenceRef: string;
    };

export type StoreDeliveryCheck =
  | NotRunCheck
  | {
      status: "declared";
      artifactRef: string;
      sha256: string;
      method: string;
      observedAt: string;
      evidenceRef: string;
    }
  | {
      status: "manually-reviewed";
      artifactRef: string;
      sha256: string;
      method: string;
      observedAt: string;
      evidenceRef: string;
      reviewer: string;
      reviewedAt: string;
      reviewEvidenceRef: string;
    };

export type StoreCheck =
  | NotRunCheck
  | {
      status: "uploaded" | "reviewed" | "released";
      publishingArtifactRef: string;
      storeBuildRef: string;
      track: string;
      observedAt: string;
      evidenceRef: string;
      deliveredBytes: StoreDeliveryCheck;
    };

export type ReleaseEvidence = {
  schemaVersion: 2;
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
    runtimeFingerprintOrPolicy: string;
  };
  artifacts: ArtifactEvidence[];
  signing: SigningCheck[];
  installation: InstallationCheck;
  store: StoreCheck;
  limitations: string[];
};

export type ArtifactSetAssessment = {
  publishingOrArchiveIdentified: boolean;
  installableCandidateIdentified: boolean;
  releaseCandidateArtifactSetComplete: boolean;
};

export type SigningSummary = {
  notRun: number;
  claimed: number;
  manuallyReviewed: number;
};

export type StoreDeliveryReviewState = StoreDeliveryCheck["status"];

export type ValidationResult =
  | {
      ok: true;
      evidence: ReleaseEvidence;
      artifactRoles: Record<string, ArtifactRole>;
      artifactSet: ArtifactSetAssessment;
      signingSummary: SigningSummary;
      installationEvidenceConsistent: boolean;
      physicalDeviceEvidenceConsistent: boolean;
      storeDeliveryReviewState: StoreDeliveryReviewState;
    }
  | { ok: false; errors: string[] };

export type CrossPlatformAssessment = {
  sameSource: boolean;
  androidArtifactSetComplete: boolean;
  iosArtifactSetComplete: boolean;
  androidPhysicalDeviceEvidenceConsistent: boolean;
  iosPhysicalDeviceEvidenceConsistent: boolean;
  crossPlatformPhysicalDeviceEvidenceConsistent: boolean;
  errors: string[];
};
