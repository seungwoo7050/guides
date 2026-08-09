# 안전·환경·증거 계약

이 가이드의 기본 실행 경로는 로컬 Python 3.10 이상과 표준 라이브러리만 사용한다. 필수 검사에는 외부 서비스, 게임 엔진 설치, 계정, 유료 cloud 자원, 실제 배포나 외부 시스템 변경이 없다. 입력은 저장소에 포함된 합성 fixture이며 실제 사용자·production 데이터가 아니다.

## 데이터와 비밀정보

- fixture에는 합성 player/session/build id만 사용한다.
- API key, access token, cookie, 개인 식별 정보, 실제 crash dump·save·telemetry를 커밋하지 않는다.
- 실제 프로젝트 증거가 필요하면 secret과 개인 정보를 제거하고 최소 재현으로 축소한다. 제거할 수 없는 자료는 이 공개 브랜치에 제출하지 않는다.
- 실행 결과에는 명령, source/build/content identity와 필요한 관측값만 남기고 환경 전체나 credential-bearing 설정을 덤프하지 않는다.
- `.guide/`, Python cache, log, build·dist·out과 editor 개인 설정은 [`.gitignore`](../.gitignore) 대상이다.

## 격리된 학습자 작업 공간

추적된 template, starter, reference와 fixture를 직접 수정해 제출하지 않는다. 저장소 밖의 존재하지 않는 절대 경로를 지정한다.

```sh
WORK_PARENT="$(mktemp -d)"
./scripts/new-workspace.sh "$WORK_PARENT/game-development"
```

생성기는 다음 안전 조건을 강제한다.

- 기존 경로와 symlink를 거부한다.
- 저장소 자신, 저장소 안쪽과 저장소의 상위 경로를 거부한다.
- 임시 sibling 디렉터리에 복사한 뒤 원자적으로 목적 이름을 공개한다.
- 단계 실습은 `submission/`, Capstone은 `submission/`과 `starter/` 복사본만 만든다.
- 검사기는 `--submission` 또는 `--implementation`으로 전달한 경로를 읽으며 추적 source를 덮어쓰지 않는다.

학습자 workspace는 사용자의 작업이므로 `make clean`이 삭제하지 않는다. 더 이상 필요 없을 때 사용자가 위에서 자신이 만든 정확한 경로를 확인한 뒤 직접 정리한다.

## 준비·검증·정리 범위

```sh
./prepare.sh
./verify.sh
make clean
```

`prepare.sh`는 `.guide/game-development/prepared.json`에 Python 판본, 현재 Git HEAD와 source fingerprint만 기록한다. `verify.sh`는 marker가 현재 source와 HEAD에 대응하는지 확인하고 필수 검사를 생략하지 않는다. 검증 전후 fingerprint가 달라지면 실패한다.

`make clean`의 삭제 범위는 저장소 내부 `.guide/game-development` marker와 Python `__pycache__`, `.pyc`, `.pyo`뿐이다. 학습자 workspace, fixture, reference, 제출물, 다른 `.guide` 하위 경로나 임의 실행 결과는 삭제하지 않는다. Capstone evidence를 정리할 때도 사용자가 명시한 실행별 출력 경로만 대상으로 삼는다.

## 위험·권한·비용 경계

- 기본 실습은 네트워크를 열거나 실제 server/client transport를 실행하지 않는다. network fixture는 latency·loss·reordering 사건을 합성한다.
- 기본 profile 수치는 결정적 counter와 modeled timing이며 target hardware 측정값으로 주장하지 않는다.
- 실제 엔진·기기 대체 경로는 별도 project sandbox, 최소 권한, version control과 backup을 사용한다. platform signing, store upload, live matchmaking, telemetry 전송과 cloud build는 이 가이드의 승인 범위 밖이다.
- 실제 service·장비가 없으면 headless 경로로 state transition, replay, authority와 resource 불변식을 검증할 수 있다. 그 대체 경로는 engine callback, GPU, platform lifecycle/storage와 실제 transport를 증명하지 않는다.
- 공식 자료 링크 확인을 제외한 필수 검사는 offline이다. 링크 변화나 문서 version은 [공식 자료 지도](../docs/90-engine-and-source-map.md)의 확인일과 함께 재검토한다.

## 라이선스와 출처

- Markdown 설명·표·그림은 [CC BY 4.0](../LICENSES/CC-BY-4.0.txt)이다.
- Python·shell·Makefile, 설정 예제와 합성 JSON/CSV fixture는 [MIT](../LICENSES/MIT.txt)이다.
- 외부 엔진·플랫폼 자료는 링크와 개념 교차 확인에만 사용하며 문장·코드·그림을 복제하지 않는다. 외부 project 증거에는 해당 project와 dependency의 license가 우선한다.

## 사람이 최종 확인할 항목

- 제출 증거에 비밀정보·실데이터·제3자 저작물이 없는가
- 실제 엔진 대체 경로의 project/build/content revision과 재현 명령이 정확한가
- target hardware의 frame/resource/loading capture가 같은 workload에서 수집됐는가
- 접근성, suspend/resume, storage durability와 실제 network transport 주장이 실제 환경 근거를 갖는가
- 알려진 한계, cleanup·rollback과 남은 위험이 release 판단에 연결됐는가

자동 검사 성공은 이 질문에 대한 사람의 확인을 대신하지 않는다.
