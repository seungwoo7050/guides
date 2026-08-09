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
