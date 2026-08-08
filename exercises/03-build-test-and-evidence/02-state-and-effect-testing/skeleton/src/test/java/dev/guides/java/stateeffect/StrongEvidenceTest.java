package dev.guides.java.stateeffect;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.HashSet;
import org.junit.jupiter.api.Test;

class StrongEvidenceTest {
  @Test
  void provesOneStateChangeAndEffectForRepeatedKey() {
    StateStore stateStore = new StateStore();
    ExternalEffect effect = new ExternalEffect();
    var service = new IdempotentOperationService(1_000, stateStore, effect);
    var ids = new HashSet<String>();

    for (int i = 0; i < 20; i++) {
      ids.add(service.apply("same-key", 100).operationId());
    }

    assertThat(ids).hasSize(1);
    assertThat(service.currentValue()).isEqualTo(900);
    assertThat(stateStore.changes()).hasSize(1);
    assertThat(stateStore.netChange()).isEqualTo(-100);
    assertThat(effect.calls()).hasSize(1);
  }
}
