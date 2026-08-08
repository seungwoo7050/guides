# 운영 계약과 위협 모델

이 실습은 공개 서비스를 만들기 전에 운영 목표와 잔여 위험을 구조화합니다. 기술 이름을 많이 적는 것이 아니라, 사용자 기능·정본 데이터·복구 목표·권한 경계와 소유자를 연결해야 합니다.

관련 문서: [`docs/08-production-contract-and-threat-model.md`](../../docs/08-production-contract-and-threat-model.md)

## 시작 상태

```text
skeleton/contract.yaml
```

에는 일부 항목만 있습니다. 다음을 완성합니다.

- 사용자 능력으로 표현한 서비스 설명
- 공개 endpoint와 제한된 관리 endpoint
- 업무 데이터·비밀값·운영 설정의 정본과 복구 원본
- 측정 경로가 있는 가용성 목표
- RTO와 RPO
- trust boundary와 대표 위험
- 각 위험의 예방·탐지·복구
- 단일 호스트에서 수용하는 잔여 위험
- release·backup·rollback·인증서·복원 훈련 준비 조건

## 검증

```sh
cd exercises/08-production-contract
./verify.sh skeleton
```

완성 전에는 실패해야 합니다. 작업 뒤 같은 명령이 통과해야 합니다.

비교용 구현:

```sh
./verify.sh reference
```

## 완료 조건

검사가 YAML의 존재만 확인한다고 생각하지 않습니다. 다음 질문에 문서의 실제 값으로 답할 수 있어야 합니다.

1. 사용자가 사용할 수 있어야 하는 핵심 기능은 무엇인가?
2. 호스트 전체 손실 뒤 어느 데이터를 어디에서 복원하는가?
3. 허용 가능한 데이터 손실과 복구 시간은 얼마인가?
4. SSH와 Docker daemon은 누가 접근하는가?
5. 공격이나 실수 하나가 backup까지 삭제할 수 있는가?
6. 단일 호스트 구조가 제거하지 못하는 위험은 무엇인가?
