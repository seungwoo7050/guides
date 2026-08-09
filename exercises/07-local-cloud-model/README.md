# 07. 로컬 Cloud 상태 모델

## 목적

실제 cloud provider emulator를 만들지 않습니다. cloud application이 지켜야 하는 다음 불변식을 작은 Python 상태 모델로 검증합니다.

```text
stateful resource는 public이 아닙니다.
cross-tenant read는 거부됩니다.
quota 초과는 partial state를 남기지 않습니다.
같은 event는 output과 usage를 한 번만 만듭니다.
terminal failure는 bounded retry 뒤 dead-letter됩니다.
tenant deletion 뒤 active data·event·resource가 남지 않습니다.
```

## 구조

```text
skeleton/cloud_model.py   의도적으로 잘못된 구현
reference/cloud_model.py  공개 계약을 만족하는 비교 구현
tests/test_cloud_model.py 외부 행동과 불변식 검사
```

## 시작

원본 skeleton은 루트 검증이 실패 profile로 사용하므로 직접 수정하지 않습니다.

```sh
mkdir -p .workspace/local-cloud-model
cp exercises/07-local-cloud-model/skeleton/cloud_model.py \
  .workspace/local-cloud-model/cloud_model.py
```

테스트에서 `CLOUD_MODEL_PROFILE` 대신 직접 경로를 쓰고 싶다면 별도 test copy를 만들 수 있습니다. 가장 단순한 학습 방법은 skeleton 디렉터리를 복사한 임시 브랜치에서 public tests를 실행하는 것입니다.

기준 profile을 확인합니다.

```sh
CLOUD_MODEL_PROFILE=reference \
python3 -m unittest discover -s exercises/07-local-cloud-model/tests -v
```

취약 profile은 실패해야 합니다.

```sh
CLOUD_MODEL_PROFILE=skeleton \
python3 -m unittest discover -s exercises/07-local-cloud-model/tests -v
```

## 수정 순서

1. stateful resource의 network exposure를 수정합니다.
2. document ownership과 tenant context를 검사합니다.
3. quota check와 write를 하나의 원자적 상태 전이로 만듭니다.
4. event ID를 사용해 output과 usage를 deduplicate합니다.
5. retry attempt와 terminal dead-letter를 구현합니다.
6. tenant deletion이 모든 active subsystem에 전파되게 합니다.

## 이 모델이 보장하지 않는 것

- 실제 provider IAM·network 동작
- distributed transaction
- queue ordering과 crash recovery
- concurrent process 사이 원자성
- 실제 billing 정확성
- physical deletion

실제 프로젝트에서는 database constraint, transaction, queue semantics와 provider integration test가 추가로 필요합니다.
