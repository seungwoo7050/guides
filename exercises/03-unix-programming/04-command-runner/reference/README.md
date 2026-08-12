# command-runner 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 source/runtime 순서가 아니라 parsing을 완성한 뒤에만 실행 자원을 여는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | 성장 가능한 word builder의 메모리 소유권을 만듭니다. |
| `2` | command와 pipeline이 word·argv 수명을 단독 소유하게 합니다. |
| `3` | quote, escape와 빈 인자를 포함한 word parser를 구현합니다. |
| `4` | 전체 line의 문법과 제한을 검증하고 성공할 때만 pipeline을 commit합니다. |
| `5` | wait/status 변환과 FD duplicate·close 규칙을 분리합니다. |
| `6` | 자식 실행 경계에서 FD를 정리하고 `exec` 실패를 126·127로 끝냅니다. |
| `7` | 단일 command와 두-command pipeline의 성공·부분 실패 cleanup을 구현합니다. |
| `8` | main이 parsing 성공 뒤에만 실행하고 두 수명 계층을 모두 정리합니다. |

별도 parser generator, project/dependency bootstrap이 없어 `Implementation 0`과 중간 CLI 단계는 없습니다.
