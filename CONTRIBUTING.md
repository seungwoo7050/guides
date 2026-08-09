# 기여 안내

이 브랜치는 모바일 library 목록을 늘리는 문서가 아니라 실행 수명·상태·권한·실패·검증 경계를 가르친다.

## 변경 원칙

- React·TypeScript·HTTP 기초를 다시 설명하지 않는다.
- Android와 iOS의 차이를 “framework가 처리한다”는 말로 숨기지 않는다.
- API 이름보다 누가 상태를 소유하고 중단·거절·재시작 뒤 어떻게 수렴하는지 먼저 설명한다.
- background 실행, network 연결, notification delivery를 보장처럼 표현하지 않는다.
- 민감정보·permission·store 정책은 최신 공식 문서와 실제 build로 확인한다.
- 새 실습은 최소 하나의 정상, 경계, 실패와 복구 조건을 가져야 한다.
- 완성된 reference를 추가할 때 skeleton이 의도대로 실패하고 검사기가 잘못된 구현을 거부하는지 확인한다.

## 문서 변경 검사

```sh
./prepare.sh
./verify.sh
```

새 문서에는 목적, 상태와 소유자, 대표 실패, 검증 방법, 연결 실습 또는 실제 프로젝트 전환점을 포함한다.

## 독립 브랜치 commit history

`mobile-app`은 `main`의 snapshot을 한 번에 복사한 history가 아니라 학습자가 변화 이유를 따라갈 수 있는 독립 history를 유지한다.

```text
기초 repository 구성
→ 대상·범위·roadmap
→ 개념 단원
→ 해당 단계 skeleton/reference와 행동 검사
→ 누적 capstone
→ prepare/verify
→ 실제 검증에서 발견한 품질 보정
```

- 문서·실습·검증을 모두 작성한 뒤 하나의 거대한 commit으로 넣지 않는다.
- 각 commit은 한 개념 또는 한 실행 가능한 학습 단위를 설명하는 subject와 범위를 가진다.
- 의도적 skeleton 실패와 reference 통과를 같은 공개 계약으로 관찰할 수 있는 지점에서 기록한다.
- review를 숨기는 `fixup!`, 사후 squash, amend·rebase로 이미 공개한 학습 단위를 다시 쓰지 않는다.
- 품질 검사에서 발견한 실제 결함은 원래 단위를 고쳐 쓴 것처럼 숨기지 않고 원인과 회귀 근거가 드러나는 후속 `fix` 또는 `test` commit으로 남긴다.
- `main`, catalog, 생성 문서와 다른 branch를 이 history에서 수정하지 않는다.

commit 수가 많다는 사실만으로 좋은 history가 되지는 않는다. 각 지점에서 “무엇을 배울 수 있고, 어떤 검사가 아직 실패하며, 다음 commit이 어떤 계약을 추가하는가”를 설명할 수 있어야 한다.
