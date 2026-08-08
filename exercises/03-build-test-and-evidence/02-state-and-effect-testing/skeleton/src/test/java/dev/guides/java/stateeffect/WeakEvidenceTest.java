package dev.guides.java.stateeffect;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class WeakEvidenceTest {
  @Test
  void onlyChecksThatCallsReturned() {
    var service = new IdempotentOperationService(1_000, new StateStore(), new ExternalEffect());
    for (int i = 0; i < 20; i++) {
      assertThat(service.apply("same-key", 100)).isNotNull();
    }
  }
}
