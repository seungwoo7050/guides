package dev.guides.java.firstprogram;

import java.io.PrintStream;

public final class NumberReportApplication {
  private NumberReportApplication() {}

  public static void main(String[] args) {
    int status = run(args, System.out, System.err);
    if (status != 0) {
      System.exit(status);
    }
  }

  public static int run(String[] args, PrintStream output, PrintStream error) {
    // TODO: 입력 검증, 정확한 합계와 출력 경계를 구현합니다.
    output.println("count=" + args.length);
    return 0;
  }
}
