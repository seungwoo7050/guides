package dev.guides.distributed.observability;

import dev.guides.distributed.testing.Checks;
import java.util.List;
import java.util.Set;

public final class ObservabilityCorrelationTest {
    public static void main(String[] args) {
        identifiersRemainConnectedAcrossHops();
        duplicateDeliveryIsVisibleWithoutDuplicateEffect();
        metricsUseBoundedTagKeys();
        traceAndMetricContractsAreExplicit();
    }

    private static void identifiersRemainConnectedAcrossHops() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-17", "op-42", "reservation-9");
        ObservabilityCorrelation.Event event = flow.publish(command);
        flow.consume(event);

        List<ObservabilityCorrelation.Observation> observations = flow.observations();
        Checks.equals(3, observations.size(), "세 처리 경계의 관찰값이 필요합니다");
        for (ObservabilityCorrelation.Observation observation : observations) {
            Checks.equals(
                "req-17",
                observation.correlationId(),
                "모든 hop이 같은 correlation ID를 유지해야 합니다"
            );
            Checks.equals(
                "trace-req-17",
                observation.traceId(),
                "모든 hop이 같은 trace ID를 유지해야 합니다"
            );
            Checks.equals(
                "op-42",
                observation.operationId(),
                "모든 hop이 재시도 전체 operation ID를 유지해야 합니다"
            );
        }
        Checks.equals(
            "op-42",
            event.causationId(),
            "이벤트가 어떤 명령 때문에 만들어졌는지 남겨야 합니다"
        );
        Checks.equals("reservation-9", event.aggregateId(), "업무 대상 ID를 보존해야 합니다");
    }

    private static void duplicateDeliveryIsVisibleWithoutDuplicateEffect() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-18", "op-43", "reservation-10");
        ObservabilityCorrelation.Event event = flow.publish(command);

        flow.consume(event);
        flow.consume(event);

        Checks.equals(1, flow.effects(), "같은 이벤트의 업무 효과는 하나여야 합니다");
        Checks.equals(
            1,
            flow.metricCount("inventory", "duplicate"),
            "중복 처리 시도는 별도 결과로 관찰해야 합니다"
        );
    }

    private static void metricsUseBoundedTagKeys() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        Checks.equals(
            Set.of("component", "outcome"),
            flow.metricTagKeys(),
            "metric tag에 요청별 식별자를 넣으면 안 됩니다"
        );
    }

    private static void traceAndMetricContractsAreExplicit() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-19", "op-44", "reservation-11");
        Checks.isFalse(
            command.traceId().equals(command.operationId()),
            "trace와 업무 operation은 서로 다른 수명 주기를 표현해야 합니다"
        );
        flow.validateMetricTagKeys(Set.of("component", "outcome"));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> flow.validateMetricTagKeys(Set.of("component", "operationId")),
            "고카디널리티 식별자를 metric tag로 허용하면 안 됩니다"
        );
    }
}
