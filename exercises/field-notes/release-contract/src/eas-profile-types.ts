export type PublicEasBuildProfile =
  | "development"
  | "preview"
  | "production";

export type EasDistribution = "internal" | "store";
export type EasAndroidBuildType = "apk" | "app-bundle";

export type EasPlatformProfile = {
  node?: string;
  distribution?: EasDistribution;
  env?: Record<string, string>;
};

export type EasAndroidProfile = EasPlatformProfile & {
  buildType?: EasAndroidBuildType;
};

export type EasBuildProfile = {
  extends?: string;
  node?: string;
  developmentClient?: boolean;
  distribution?: EasDistribution;
  environment?: string;
  env?: Record<string, string>;
  android?: EasAndroidProfile;
  ios?: EasPlatformProfile;
};

export type ValidatedEasConfiguration = {
  cli: {
    requireCommit: true;
    appVersionSource: "local";
  };
  build: {
    development: EasBuildProfile;
    preview: EasBuildProfile;
    production: EasBuildProfile;
    base?: EasBuildProfile;
  };
};

export type ResolvedEasProfileAssessment = {
  profile: PublicEasBuildProfile;
  inheritanceChain: string[];
  node: {
    root: "24.19.0";
    android: "24.19.0";
    ios: "24.19.0";
    inherited: boolean;
  };
  developmentClient: boolean;
  distribution: {
    android: EasDistribution;
    ios: EasDistribution;
    androidDefaulted: boolean;
    iosDefaulted: boolean;
  };
  androidBuild: {
    type: EasAndroidBuildType;
    source:
      | "explicit"
      | "development-client"
      | "internal-distribution"
      | "eas-default";
  };
  environment: PublicEasBuildProfile;
  profileLabel: PublicEasBuildProfile;
};

export type EasProfileContractGuarantees = {
  configurationShapeValidated: boolean;
  nativeBuildExecuted: false;
  artifactBytesProducedOrInspected: false;
  signingOrCredentialsValidated: false;
  applicationInstalledOrLaunched: false;
  storeUploadOrAcceptanceValidated: false;
  easUpdatePublishedOrDelivered: false;
  stableApprovalGranted: false;
};

export type EasProfileContractAssessment = {
  contract: "field-notes-eas-build-profiles-v1";
  configurationValid: boolean;
  sourcePolicy: {
    requireCommit: boolean;
    appVersionSource: string | null;
  };
  profiles: Partial<
    Record<PublicEasBuildProfile, ResolvedEasProfileAssessment>
  >;
  guarantees: EasProfileContractGuarantees;
  errors: string[];
};

export type EasProfileValidationResult =
  | {
      ok: true;
      config: ValidatedEasConfiguration;
      assessment: EasProfileContractAssessment & {
        configurationValid: true;
        guarantees: EasProfileContractGuarantees & {
          configurationShapeValidated: true;
        };
        errors: [];
      };
    }
  | {
      ok: false;
      errors: string[];
      assessment: EasProfileContractAssessment & {
        configurationValid: false;
        guarantees: EasProfileContractGuarantees & {
          configurationShapeValidated: false;
        };
      };
    };
