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

`make check`와 `verify.sh`는 로컬 file·heading·fragment만 자동 확인하고 외부 HTTP(S)·`mailto`의 현재 상태는 사람이 확인할 범위로 출력합니다. `verify.sh`는 모든 필수 검사와 meta-test를 저장소 밖 임시 복사본에서 실행하고 원본 source와 `.workspace/`가 바뀌지 않았는지 비교합니다.

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

# report는 새 파일만 만들며 기존 파일을 덮어쓰지 않습니다.
report_dir=$(mktemp -d)
python3 scripts/verify_cloud_model.py \
  --implementation exercises/07-local-cloud-model/reference/cloud_model.py \
  --report "$report_dir/cloud-model-report.json"

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
