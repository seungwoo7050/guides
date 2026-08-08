package dev.guides.distributed.boundary;

import java.util.ArrayList;
import java.util.List;
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
        List<String> issues = new ArrayList<>();
        for (DataSet dataSet : architecture.dataSets()) {
            if (dataSet.owner() == null || dataSet.owner().isBlank()) {
                issues.add("missing owner for " + dataSet.name());
            }
        }
        return List.copyOf(issues);
    }

    private ServiceBoundary() {
    }
}
