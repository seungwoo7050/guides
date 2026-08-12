# diagnostic-formatter 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 source/runtime 순서가 아니라 포맷 상태와 실패 계약을 쌓는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | 논리적 출력 길이와 실제 buffer 기록 위치를 한 상태가 소유하게 합니다. |
| `2` | 문자, 문자열, 부호 없는 수와 부호 있는 수를 같은 출력 경계로 보냅니다. |
| `3` | capacity와 관계없이 가능한 위치에 NUL terminator를 확정합니다. |
| `4` | 복사한 `va_list`로 format을 해석하고 지원하지 않는 형식을 실패로 끝냅니다. |
| `5` | variadic wrapper가 `va_list` 수명을 열고 닫습니다. |

별도 framework/codegen/bootstrap이 없어 `Implementation 0`과 중간 CLI 단계는 없습니다.
