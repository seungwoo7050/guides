package dev.guides.contract;

// [Implementation 1-1] artifact consumer에게 노출할 최소 public contract를 제공합니다.
public record ContractVersion(String value) {
  public static ContractVersion current() {
    return new ContractVersion("1.0-SNAPSHOT");
  }
}
