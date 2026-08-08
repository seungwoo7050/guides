package dev.guides.java.runtime;

import java.nio.charset.Charset;
import java.time.ZoneId;

public final class RuntimeProbe {
  private RuntimeProbe() {}

  public static void main(String[] args) {
    System.out.printf("java.version=%s%n", System.getProperty("java.version"));
    System.out.printf("java.home=%s%n", System.getProperty("java.home"));
    System.out.printf("os.name=%s%n", System.getProperty("os.name"));
    System.out.printf("os.arch=%s%n", System.getProperty("os.arch"));
    System.out.printf("charset=%s%n", Charset.defaultCharset());
    System.out.printf("timezone=%s%n", ZoneId.systemDefault());
  }
}
