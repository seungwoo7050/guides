# 공개 TLS 수명 주기

공인 도메인 없이 로컬 CA를 사용해 인증서의 발급·검증·원자 교체와 만료 검사 경계를 재현합니다.

관련 문서: [`docs/10-dns-acme-and-public-tls.md`](../../docs/10-dns-acme-and-public-tls.md)

## 구현할 명령

```sh
./tls-lifecycle.sh issue WORKDIR HOSTNAME DAYS
./tls-lifecycle.sh renew WORKDIR HOSTNAME DAYS
./tls-lifecycle.sh verify WORKDIR HOSTNAME MIN_REMAINING_DAYS
```

`issue`와 `renew`는 다음을 만족해야 합니다.

- root CA가 없으면 안전한 권한으로 생성
- server key를 mode 600으로 생성
- SAN에 정확한 hostname 포함
- 임시 파일을 먼저 검증한 뒤 현재 certificate 교체
- private key나 passphrase를 stdout에 출력하지 않음

`verify`는 다음을 모두 검사해야 합니다.

- CA chain
- hostname
- 최소 남은 유효기간
- key 파일 권한

## 검증

```sh
cd exercises/10-public-tls
./verify.sh skeleton
./verify.sh reference
```

검증기는 올바른 hostname 성공, 잘못된 hostname 거부, 짧은 인증서 거부와 renewal 뒤 serial 변경을 확인합니다. 공개 운영에서 `curl -k`로 성공을 만들면 안 되는 이유를 설명할 수 있어야 합니다.

이 실습의 root CA는 인증서 검증 흐름을 로컬에서 재현하기 위한 임시 자산입니다. 실제 공개 서비스에서는 임의의 로컬 CA를 브라우저 신뢰 저장소에 배포하는 방식으로 대체하지 않으며, CA 개인키를 gateway나 application host에 복사하지 않습니다.

## 완료 기준

- [ ] `./verify.sh skeleton`이 통과하고 올바른 hostname·충분한 유효기간만 허용하며 잘못된 hostname·짧은 인증서를 거부한다.
- [ ] server key mode가 600이고 명령 출력에 key나 passphrase가 없으며 CA key와 service key의 소유 경계가 분리된다.
- [ ] renewal 성공 시 serial이 바뀌고 후보 검증 실패 시 기존 인증서가 그대로 유지되는 원자 교체를 확인한다.

## 자기 설명

1. CA chain, hostname, 남은 유효기간 검사는 각각 어떤 서로 다른 신뢰 조건을 확인하는가?
2. 인증서와 key를 임시 경로에서 검증한 뒤 함께 전환해야 하는 이유는 무엇인가?
3. `curl -k`가 연결 문제를 숨기면서도 운영 TLS 검증을 완료한 증거가 될 수 없는 이유는 무엇인가?
