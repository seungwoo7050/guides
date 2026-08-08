package dev.guides.distributed.boundary;

import dev.guides.distributed.testing.Checks;
import java.util.List;
import java.util.Set;

public final class ServiceBoundaryTest {
    public static void main(String[] args) {
        validOwnershipAndDirectionPass();
        sharedWriteAndMissingOwnerWriterFail();
        unknownReferencesFail();
        synchronousCycleFails();
    }

    private static ServiceBoundary.Service service(String name, String... dependencies) {
        return new ServiceBoundary.Service(name, Set.of(dependencies));
    }

    private static void validOwnershipAndDirectionPass() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(
                service("gateway", "reservation"),
                service("reservation", "inventory"),
                service("inventory")
            ),
            List.of(
                new ServiceBoundary.DataSet(
                    "reservations",
                    "reservation",
                    Set.of("reservation")
                ),
                new ServiceBoundary.DataSet(
                    "stock",
                    "inventory",
                    Set.of("inventory")
                )
            )
        );

        Checks.equals(
            List.of(),
            ServiceBoundary.review(architecture),
            "단일 writer와 단방향 의존은 통과해야 합니다"
        );
    }

    private static void sharedWriteAndMissingOwnerWriterFail() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(service("reservation"), service("inventory")),
            List.of(
                new ServiceBoundary.DataSet(
                    "stock",
                    "inventory",
                    Set.of("inventory", "reservation")
                ),
                new ServiceBoundary.DataSet(
                    "reservations",
                    "reservation",
                    Set.of()
                )
            )
        );

        String issues = String.join("\n", ServiceBoundary.review(architecture));
        Checks.contains(issues, "non-owner writer for stock", "공유 쓰기를 찾아야 합니다");
        Checks.contains(
            issues,
            "owner is not a writer for reservations",
            "소유자가 변경 주체에서 빠진 상태를 찾아야 합니다"
        );
    }

    private static void unknownReferencesFail() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(service("reservation", "missing-service")),
            List.of(
                new ServiceBoundary.DataSet(
                    "audit",
                    "missing-owner",
                    Set.of("missing-writer")
                )
            )
        );

        String issues = String.join("\n", ServiceBoundary.review(architecture));
        Checks.contains(issues, "unknown owner", "등록되지 않은 소유자를 찾아야 합니다");
        Checks.contains(issues, "unknown writer", "등록되지 않은 writer를 찾아야 합니다");
        Checks.contains(issues, "unknown dependency", "등록되지 않은 의존 대상을 찾아야 합니다");
    }

    private static void synchronousCycleFails() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(
                service("orchestrator", "inventory"),
                service("inventory", "orchestrator")
            ),
            List.of()
        );

        String issues = String.join("\n", ServiceBoundary.review(architecture));
        Checks.contains(
            issues,
            "synchronous dependency cycle",
            "동기 의존 순환을 찾아야 합니다"
        );
    }
}
