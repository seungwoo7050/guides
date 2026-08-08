package dev.guides.contract;

public record ContractVersion(String value) {
  public static ContractVersion current() {
    return new ContractVersion("1.0-SNAPSHOT");
  }
}
