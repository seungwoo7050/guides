#!/usr/bin/env python3
"""읽기-수정-쓰기의 잃어버린 갱신을 결정적으로 재현한다."""

# [Implementation 1] 두 요청이 같은 shared state를 읽은 stale snapshot을 먼저 고정한다.
balance = 10
first_read = balance
second_read = balance

# [Implementation 2] 두 snapshot의 write를 순서대로 적용해 last-writer effect와 금지 결과를 드러낸다.
balance = first_read - 7
balance = second_read - 7

assert balance == 3
assert balance != -4  # 두 성공을 모두 반영한 결과가 아니다.
print("transaction anomaly example: PASS")
