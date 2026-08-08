package dev.guides.java.firstprogram;

import java.io.PrintStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;

public final class NumberReportApplication {
  private static final int INVALID_INPUT = 2;

  private NumberReportApplication() {}

  public static void main(String[] args) {
    int status = run(args, System.out, System.err);
    if (status != 0) {
      System.exit(status);
    }
  }

  public static int run(String[] args, PrintStream output, PrintStream error) {
    if (args.length == 0) {
      error.println("오류: 하나 이상의 정수를 입력하십시오.");
      return INVALID_INPUT;
    }

    long minimum = Long.MAX_VALUE;
    long maximum = Long.MIN_VALUE;
    long sum = 0L;

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
