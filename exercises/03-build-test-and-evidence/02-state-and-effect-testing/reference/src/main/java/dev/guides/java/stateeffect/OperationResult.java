package dev.guides.java.stateeffect;

// [Implementation 1] 반복 호출이 함께 관찰할 immutable completion evidence를 정의합니다.
public record OperationResult(String operationId, long currentValue) {}
