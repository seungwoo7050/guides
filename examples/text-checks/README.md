# Unix 텍스트 검사 관찰

결정적인 로그 fixture를 대상으로 stdout·stderr·종료 상태를 분리하고 `cmp`, `diff`, `grep`, `sed`, `awk`를 서로 다른 증거에 사용합니다. 이 예제에서는 `tests/check.sh` 자체가 학습할 완성 구현이며, `src/loggen.sh`는 입력 fixture입니다.

## 실행

```sh
make check
```

## 구현 순서

아래 번호는 실제 Git 작성 이력이 아니라, 좁은 검사에서 상태 기반 검증으로 확장하는 권장 순서입니다.

| 순서 | 위치 | 먼저 고정하는 책임 |
|---:|---|---|
| `1` | 임시 디렉터리와 usage 검사 | 채널과 종료 상태를 서로 다른 evidence로 보존합니다. |
| `2` | `cmp`, `diff` 검사 | byte-exact 결과와 사람이 읽을 차이를 구분합니다. |
| `3` | `grep`, `sed` 검사 | 한 줄 조건과 정규화 뒤 조건을 좁게 확인합니다. |
| `4` | `validate`의 `awk` 상태 | id별 종료 불변식을 여러 줄에 걸쳐 검사합니다. |
| `5` | known-bad와 error case | 검사기가 실제 실패와 채널 오류를 거부하는지 확인합니다. |

이 scope에는 application bootstrap이나 중간 생성 CLI가 없으므로 Implementation 0은 없습니다.
