# 기여 안내

문서, 실습 계약과 검증 도구는 같은 그래픽스 규약을 가리켜야 합니다. 새 효과나 API 이름을 추가하는 것보다 어떤 상태가 바뀌고, 어떤 실패가 생기며, 어떤 artifact가 결과를 증명하는지 먼저 명확히 합니다.

## 범위와 소유권

이 브랜치는 다음을 소유합니다.

- 좌표 공간에서 frame pixel까지의 graphics pipeline
- rasterization·sampling·depth·blend·lighting의 그래픽스 계약
- mesh·texture·scene asset의 renderable validation
- GPU resource·shader·pipeline·command·frame lifecycle
- frame capture, image oracle와 graphics performance evidence

다음은 다른 브랜치 또는 후속 전문 과정의 소유입니다.

- C++ 문법·RAII·CMake 일반 과정: `cpp`
- 자료구조·복잡도·기준 구현: `algorithms`
- cache·SIMD·멀티코어 일반 원리: `computer-architecture`
- 게임플레이·물리·오디오·게임 엔진 제품 전체
- ray/path tracing, advanced PBR, GPU driver/compiler 전문 과정

같은 설명을 복사하지 않고 필요한 접점만 링크합니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- API, 타입, 수식과 식별자는 원래 표기와 백틱을 사용합니다.
- 좌표·단위·범위·색 encoding·alpha 표현을 값 이름에 드러냅니다.
- 정의 나열보다 상태, 소유권, 실패 조건과 검증 방법을 우선합니다.
- 특정 API의 최신 사실은 공식 문서와 확인 날짜를 기록합니다.
- 성능·정확성·이식성을 실행 근거 없이 단정하지 않습니다.
- 외부 문서의 표와 코드를 복제하지 않고 자체 설명과 fixture를 만듭니다.

핵심 문서 `01–20`은 최소한 다음 절을 유지합니다.

```text
목표
시작하기 전에
연결 실습
완료 기준
```

모든 문서에 동일한 세부 목차를 기계적으로 복제하지 않습니다.

## 규약을 바꿀 때

좌표·색·alpha·sample 규약은 다음 파일을 함께 검토합니다.

```text
docs/00-roadmap.md
docs/90-appendix/01-math-conventions-and-formulas.md
reference/formulas-and-checklist.md
관련 실습 contract.json
```

reference image를 새 결과로 덮어쓰는 것으로 변경을 끝내지 않습니다. 이전/새 결과, 첫 달라진 pipeline 단계, mutation test와 migration을 기록합니다.

## 실습을 고칠 때

- `README.md`와 `contract.json`을 함께 갱신합니다.
- 초기 상태, 입력, 필수 artifact, 불변식과 완료 근거를 명시합니다.
- 정답 구현을 추가하지 않아도 학습자가 결과를 검증할 수 있어야 합니다.
- known-bad mutation은 실제로 검사기에 거부되는 오답이어야 합니다.
- image tolerance를 실패 뒤 임의로 넓히지 않습니다.
- 외부 asset을 넣을 때 source URL, content hash와 license를 기록합니다.

새 실습 contract는 `exercises/contract.schema.json`의 field를 유지합니다.

## 코드를 고칠 때

현재 실행 코드는 repository verifier와 PPM comparator입니다.

- Python 표준 라이브러리만 사용합니다.
- invalid input은 명시적 diagnostic과 non-zero exit로 거부합니다.
- self-test는 정상 결과뿐 아니라 알려진 mutation의 실패를 확인합니다.
- 원본 source와 사용자 artifact를 수정하거나 삭제하지 않습니다.
- 임시 파일은 고유 임시 디렉터리에 만들고 모든 종료 경로에서 정리합니다.

향후 renderer skeleton/reference를 추가한다면 별도 구현 프로필과 build dependency를 명시하고, 문서 검증만 필요한 환경을 불필요하게 실패시키지 않습니다.

## 변경 전 준비와 검증

```sh
./prepare.sh
make check
./verify.sh
```

`prepare.sh`는 package를 설치하지 않습니다. 선택 도구의 존재와 source 지문만 기록합니다. source를 변경했다면 다시 실행합니다.

`verify.sh`는 임시 복사본에서 다음을 검사합니다.

- 필수 구조와 핵심 문서 절
- 내부 Markdown 링크
- 실습 contract와 관련 문서
- 과정 좌표·색 규약의 정본
- PPM comparator 정상·mutation self-test
- 원본 source 지문 불변

커밋 전에는 다음도 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 버전 갱신

SDL, Vulkan, WebGPU/WGSL, RenderDoc, CMake와 glTF 기준을 갱신할 때는 공식 release/specification을 확인합니다. 문서의 숫자만 바꾸지 말고 다음을 검토합니다.

- API/ownership 변화
- shader format·binding 변화
- 좌표·format convention 영향
- build와 runtime smoke
- validation baseline
- known-bad mutation과 reference 결과

정본은 [`reference/version-baseline.md`](reference/version-baseline.md)에 기록합니다.

## 커밋 예시

```text
docs(raster): shared-edge fill rule의 경계 계약 보완
docs(gpu): frame slot 재사용과 completion 관계 명확화
test(exercise): affine UV mutation 계약 추가
tool(ppm): P6 extent 오류 진단 보완
```

서로 독립적인 개념 변경과 도구 수정은 나누어 기록합니다.
