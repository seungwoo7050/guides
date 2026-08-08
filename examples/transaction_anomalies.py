#!/usr/bin/env python3
"""읽기-수정-쓰기의 잃어버린 갱신을 결정적으로 재현한다."""

balance = 10
first_read = balance
second_read = balance
balance = first_read - 7
balance = second_read - 7

assert balance == 3
assert balance != -4  # 두 성공을 모두 반영한 결과가 아니다.
print("transaction anomaly example: PASS")
