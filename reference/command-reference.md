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
CLOUD_MODEL_PROFILE=reference \
python3 -m unittest discover -s exercises/07-local-cloud-model/tests -v

CLOUD_MODEL_PROFILE=skeleton \
python3 -m unittest discover -s exercises/07-local-cloud-model/tests -v
```

## 정리

```sh
make clean
```

`make clean`은 `.workspace/`를 삭제하지 않습니다. 학습자 작업은 직접 검토한 뒤 삭제합니다.
