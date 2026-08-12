package dev.guides.java.jobledger;

// [Implementation 2] 원장이 받을 command family를 sealed boundary로 제한합니다.
public sealed interface JobCommand permits CreditJob, DebitJob {
  JobId id();

  long amount();
}
