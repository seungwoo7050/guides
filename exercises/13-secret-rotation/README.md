# Versioned secret 회전

임시 host root에서 secret의 생성·검증·전환·폐기 순서를 구현합니다. 외부 secret manager 제품보다 실패 후 상태에 집중합니다.

관련 문서: [`docs/13-production-secrets-and-configuration.md`](../../docs/13-production-secrets-and-configuration.md)

## 구현 계약

`skeleton/rotate.py`의 `SecretStore`를 완성합니다.

- secret 디렉터리 mode 700
- secret 파일 mode 600
- versioned 파일을 임시 경로에 쓴 뒤 원자 이동
- 소비자 검증 성공 전에 current pointer 변경 금지
- 실패한 후보는 current가 되지 않음
- 이전 version은 명시적으로 retire하기 전까지 유지
- current version retire 거부
- event log에는 값이나 직접 hash가 아니라 별도 audit key를 사용한 HMAC fingerprint와 metadata만 기록
- secret 이름과 version을 검증해 저장 경로 밖으로 나가는 입력 거부

## 검증

```sh
cd exercises/13-secret-rotation
./verify.sh skeleton
./verify.sh reference
```

검증기는 실패한 v2 전환, 성공한 v2 전환, v1 폐기, 파일 권한, validator 예외 뒤 상태, HMAC fingerprint와 로그 유출을 확인합니다.

실습은 audit key를 별도 파일로 분리합니다. 실제 운영에서는 감사용 key를 회전 대상 secret과 같은 권한 경계에 두지 않고 별도 secret manager 또는 감사 시스템이 소유해야 합니다.

## 완료 기준

- [ ] `./verify.sh skeleton`이 통과하고 실패한 후보는 current가 되지 않으며 성공한 version만 원자적으로 전환된다.
- [ ] secret 디렉터리와 파일 권한, 경로 탈출 입력 거부, current version 폐기 거부를 직접 확인한다.
- [ ] event log에 secret 값이나 직접 hash가 없고 별도 audit key의 HMAC fingerprint와 필요한 metadata만 남는다.

## 자기 설명

1. 후보 생성, 소비자 검증, current 전환, 이전 version 폐기를 한 단계로 합치면 어떤 복구 선택지를 잃는가?
2. secret의 일반 hash보다 별도 key를 사용한 HMAC fingerprint가 사전 대입 공격에 더 강한 이유는 무엇인가?
3. 새 version 전환 직후 이전 version을 바로 삭제하지 않아야 하는 조건은 무엇인가?
