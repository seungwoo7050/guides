package dev.guides.distributed.boundary;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ServiceBoundary {
    // [Implementation 1] 데이터 소유권, 서비스 의존, 전체 구조를 불변 값으로
    // 먼저 모델링해 검토 중 입력이 바뀌지 않는 공통 경계를 만든다.
    public record DataSet(String name, String owner, Set<String> writers) {
        public DataSet {
            writers = Set.copyOf(writers);
        }
    }

    public record Service(String name, Set<String> synchronousDependencies) {
        public Service {
            synchronousDependencies = Set.copyOf(synchronousDependencies);
        }
    }

    public record Architecture(List<Service> services, List<DataSet> dataSets) {
        public Architecture {
            services = List.copyOf(services);
            dataSets = List.copyOf(dataSets);
        }
    }

    // [Implementation 2] review는 등록 여부와 단일 writer 위반을 모두 수집한다.
    // 첫 오류에서 멈추지 않아 한 번의 검토로 구조의 전체 결함을 드러낸다.
    public static List<String> review(Architecture architecture) {
        Set<String> serviceNames = new LinkedHashSet<>();
        List<String> issues = new ArrayList<>();
        for (Service service : architecture.services()) {
            if (!serviceNames.add(service.name())) {
                issues.add("duplicate service: " + service.name());
            }
        }

        for (DataSet dataSet : architecture.dataSets()) {
            if (!serviceNames.contains(dataSet.owner())) {
                issues.add(
                    "unknown owner for " + dataSet.name() + ": " + dataSet.owner()
                );
            }
            if (!dataSet.writers().contains(dataSet.owner())) {
                issues.add("owner is not a writer for " + dataSet.name());
            }
            for (String writer : dataSet.writers()) {
                if (!serviceNames.contains(writer)) {
                    issues.add(
                        "unknown writer for " + dataSet.name() + ": " + writer
                    );
                } else if (!writer.equals(dataSet.owner())) {
                    issues.add(
                        "non-owner writer for " + dataSet.name() + ": " + writer
                    );
                }
            }
        }

        Map<String, Set<String>> dependencies = new HashMap<>();
        for (Service service : architecture.services()) {
            dependencies.put(service.name(), service.synchronousDependencies());
            for (String dependency : service.synchronousDependencies()) {
                if (!serviceNames.contains(dependency)) {
                    issues.add(
                        "unknown dependency from " + service.name() + ": " + dependency
                    );
                }
            }
        }

        findCycles(dependencies, serviceNames, issues);
        return List.copyOf(issues);
    }

    // [Implementation 3] 각 서비스를 시작점으로 순회하되 완료 집합을 공유해,
    // 이미 판정한 하위 그래프를 다시 탐색하지 않는다.
    private static void findCycles(
        Map<String, Set<String>> dependencies,
        Set<String> services,
        List<String> issues
    ) {
        Set<String> complete = new HashSet<>();
        Set<String> visiting = new LinkedHashSet<>();
        for (String service : services) {
            visit(service, dependencies, services, visiting, complete, issues);
        }
    }

    // [Implementation 3-1] visiting은 현재 재귀 경로, complete는 판정 완료 상태다.
    // 현재 경로에 다시 들어온 서비스만 순환으로 보고 두 lifecycle을 분리한다.
    private static void visit(
        String service,
        Map<String, Set<String>> dependencies,
        Set<String> services,
        Set<String> visiting,
        Set<String> complete,
        List<String> issues
    ) {
        if (complete.contains(service)) {
            return;
        }
        if (!visiting.add(service)) {
            issues.add("synchronous dependency cycle includes: " + service);
            return;
        }
        for (String dependency : dependencies.getOrDefault(service, Set.of())) {
            if (services.contains(dependency)) {
                visit(dependency, dependencies, services, visiting, complete, issues);
            }
        }
        visiting.remove(service);
        complete.add(service);
    }

    private ServiceBoundary() {
    }
}
