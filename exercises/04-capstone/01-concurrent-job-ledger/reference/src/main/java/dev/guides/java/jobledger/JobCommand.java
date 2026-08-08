package dev.guides.java.jobledger;

public sealed interface JobCommand permits CreditJob, DebitJob {
  JobId id();

  long amount();
}
