package dev.guides.distributed.boundary;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ServiceBoundary {
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
