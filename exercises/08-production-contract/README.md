# 운영 계약과 위협 모델

이 실습은 공개 서비스를 만들기 전에 운영 목표와 잔여 위험을 구조화합니다. 기술 이름을 많이 적는 것이 아니라, 사용자 기능·정본 데이터·복구 목표·권한 경계와 소유자를 연결해야 합니다.

관련 문서: [`docs/08-production-contract-and-threat-model.md`](../../docs/08-production-contract-and-threat-model.md)

## 시작 상태

저장소 루트에서 `python3 scripts/new-workspace.py exercises/08-production-contract`를 실행하면 `workspace/contract.yaml`이 시작 상태에서 복사됩니다.

이 파일에는 일부 항목만 있습니다. 다음을 완성합니다.

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
./verify.sh workspace
```

완성 전에는 실패해야 합니다. 작업 뒤 같은 명령이 통과해야 합니다.

아래 완료 기준과 자기 설명을 끝낸 뒤에만 `reference/contract.yaml`을 expected evidence 예시로 읽고 `./verify.sh reference`와 비교합니다.

## 권장 작성 순서

`reference/contract.yaml`은 code 구현이 아니라 expected evidence입니다. 아래 번호는 실제 Git 이력이 아닌 학습용 작성 순서이며 YAML에 comment 표식을 강제하지 않습니다.

| 번호 | 작성 경계 |
|---:|---|
| [Implementation 1] | 사용자 능력과 public·management endpoint |
| [Implementation 2] | data source of truth·recovery source·RPO·owner |
| [Implementation 3] | availability·RTO·RPO objective |
| [Implementation 4] | trust boundary와 prevention·detection·recovery control |
| [Implementation 5] | residual-risk acceptance와 readiness evidence |

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 사용자 기능, 정본 데이터, RTO·RPO, trust boundary가 서로 모순 없이 연결된다.
- [ ] 각 위험에 예방·탐지·복구 수단과 owner가 있으며 단일 호스트에 남는 위험을 명시적으로 수용하거나 후속 조치로 남긴다.
- [ ] release·backup·rollback·인증서·복원 훈련의 준비 조건이 측정 가능한 증거를 가리킨다.

## 자기 설명

검사가 YAML의 존재만 확인한다고 생각하지 않습니다. 다음 질문에 문서의 실제 값으로 답합니다.

1. 사용자가 사용할 수 있어야 하는 핵심 기능은 무엇인가?
2. 호스트 전체 손실 뒤 어느 데이터를 어디에서 복원하는가?
3. 허용 가능한 데이터 손실과 복구 시간은 얼마인가?
4. SSH와 Docker daemon은 누가 접근하는가?
5. 공격이나 실수 하나가 backup까지 삭제할 수 있는가?
6. 단일 호스트 구조가 제거하지 못하는 위험은 무엇인가?
