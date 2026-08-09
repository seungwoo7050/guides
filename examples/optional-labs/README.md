# 선택 실습 fixture

이 디렉터리는 `docs/90-optional-labs/`의 local-only 입력을 제공합니다. 실제 제품이 없는 환경에서도 `python3 examples/optional-labs/check_profiles.py`로 IaC state, catalog, GitOps와 policy의 정상·대표 실패 판정을 재현할 수 있습니다.

결정적 검사는 실제 Kubernetes controller, OpenTofu/Terraform provider, Backstage ingestion, Flux/Argo CD 또는 admission webhook 동작을 증명하지 않습니다. 도구 profile을 실행했다면 별도의 version·명령·관측·cleanup evidence를 남기십시오.
