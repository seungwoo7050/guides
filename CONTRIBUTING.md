# 기여 안내

설명, fixture, exercise 계약과 자동 검사는 같은 모델 개발 수명 주기를 가리켜야 한다. 문서만 고쳤더라도 연결된 링크와 예제를 검사하고, 데이터·split·metric·artifact 계약이 서로 모순되지 않는지 확인한다.

## 문서를 고칠 때

- 자연스러운 한국어 기술 문체를 사용한다.
- API, 타입, 식별자와 수식 기호는 원래 표기를 유지하고 백틱 또는 수식 블록으로 구분한다.
- Python 문법, 알고리즘 이론, 데이터 플랫폼, agent workflow와 GPU kernel 내용을 반복하지 않는다.
- 학습 문제와 의사결정 문제, 확률과 action, validation과 final test를 분리한다.
- metric 하나나 단일 benchmark를 일반적인 품질로 과장하지 않는다.
- 특정 dataset·집단·운영 환경에서 확인하지 않은 공정성·안전성·성능 주장을 사실처럼 쓰지 않는다.
- 새로운 도구를 추가할 때는 도구 이름보다 그 도구가 고정하는 상태·artifact·실패·검증 계약을 설명한다.

## fixture와 코드를 고칠 때

- 필수 검사는 Python 표준 라이브러리만으로 실행 가능해야 한다.
- 합성 dataset은 개인·운영 데이터를 포함하지 않아야 한다.
- dataset generator와 committed CSV는 byte-for-byte 동일해야 한다.
- split은 `entity_id` 중복, 알 수 없는 split, 누락 row와 manifest 불일치를 거부해야 한다.
- 예제는 한 개념의 공개 입력·출력만 검증하며 프레임워크 내부 구현에 의존하지 않는다.
- 학습자의 `workspace/`를 자동 삭제하거나 덮어쓰지 않는다.
- `make clean`은 workspace 아래 파일을 변경하지 않는다.

## 변경 확인

```sh
./prepare.sh
./verify.sh
```

빠른 검사는 다음과 같다.

```sh
make check
```

검사기가 알려진 결함을 실제로 거부하는지는 다음으로 확인한다.

```sh
make quality-check
```

커밋 전에는 변경 범위와 공백 오류를 확인한다.

```sh
git status --short
git diff --check
git diff --staged
```
