package dev.guides.consumer;

import dev.guides.contract.ContractVersion;

// [Implementation 2-1] 설치된 contract를 사용하는 최소 consumer application 경계입니다.
public final class ConsumerApplication {
  private ConsumerApplication() {}

  public static String message() {
    return "contract=" + ContractVersion.current().value();
  }
}
