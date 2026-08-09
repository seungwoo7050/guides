# 명령 빠른 참조

## 저장소 준비와 전체 검증

```sh
./prepare.sh
./verify.sh
```

## 빠른 정적 검사

```sh
make check
```

## 문서 실습 workspace

```sh
scripts/new_workspace.sh exercises/01-service-classification
scripts/check_workspace.sh exercises/01-service-classification
```

## Capstone workspace

```sh
scripts/new_workspace.sh projects/multitenant-document-processing-saas
scripts/check_workspace.sh projects/multitenant-document-processing-saas
```

## Local model profile

```sh
python3 scripts/verify_cloud_model.py \
  --implementation exercises/07-local-cloud-model/reference/cloud_model.py

# 아래 starter는 정확히 contract.json의 8개 check에서 실패해야 합니다.
python3 scripts/verify_cloud_model.py \
  --implementation exercises/07-local-cloud-model/skeleton/cloud_model.py

# 학습자 복사본은 wrapper로 생성·검사합니다. 기존 목적지는 덮어쓰지 않습니다.
scripts/new_workspace.sh exercises/07-local-cloud-model
scripts/check_workspace.sh exercises/07-local-cloud-model
```

## 정리

```sh
make clean
```

`make clean`은 `.workspace/`를 삭제하지 않습니다. 학습자 작업은 직접 검토한 뒤 삭제합니다.
