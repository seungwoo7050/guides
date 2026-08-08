package dev.guides.consumer;

import dev.guides.contract.ContractVersion;

public final class ConsumerApplication {
  private ConsumerApplication() {}

  public static String message() {
    return "contract=" + ContractVersion.current().value();
  }
}
