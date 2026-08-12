package dev.guides.java.firstprogram;

import java.io.PrintStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;

public final class NumberReportApplication {
  private static final int INVALID_INPUT = 2;

  private NumberReportApplication() {}

  // [Implementation 2] 순수하게 반환된 상태를 실제 process exit 경계로 번역합니다.
  public static void main(String[] args) {
    int status = run(args, System.out, System.err);
    if (status != 0) {
      System.exit(status);
    }
  }

  // [Implementation 1] 입력과 두 출력 stream을 받는 application 부작용 경계를 먼저 고정합니다.
  public static int run(String[] args, PrintStream output, PrintStream error) {
    if (args.length == 0) {
      error.println("오류: 하나 이상의 정수를 입력하십시오.");
      return INVALID_INPUT;
    }

    long minimum = Long.MAX_VALUE;
    long maximum = Long.MIN_VALUE;
    long sum = 0L;

    // [Implementation 1-1] 성공 출력을 쓰기 전에 모든 입력과 checked sum을 완전히 검증합니다.
    for (String argument : args) {
      long value;
      try {
        value = Long.parseLong(argument);
      } catch (NumberFormatException exception) {
        error.println("오류: 정수가 아닙니다: " + argument);
        return INVALID_INPUT;
      }

      try {
        sum = Math.addExact(sum, value);
      } catch (ArithmeticException exception) {
        error.println("오류: 합계가 long 범위를 벗어났습니다.");
        return INVALID_INPUT;
      }
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }

    // [Implementation 1-2] locale과 반올림을 고정한 완성 결과만 stdout에 commit합니다.
    BigDecimal average =
        BigDecimal.valueOf(sum).divide(BigDecimal.valueOf(args.length), 2, RoundingMode.HALF_UP);

    output.println("count=" + args.length);
    output.println("min=" + minimum);
    output.println("max=" + maximum);
    output.println("sum=" + sum);
    output.printf(Locale.ROOT, "average=%.2f%n", average);
    return 0;
  }
}
