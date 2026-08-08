# 다중 저장소 빌드와 릴리스 명세

## 목표

여러 저장소와 산출물이 한 시스템을 구성할 때 “어떤 조합을 검증하고 배포했는가”를 고정하고, 개발 작업 트리와 릴리스 검증 환경을 분리합니다.

## 문제

각 서비스 저장소의 최신 main을 차례대로 빌드하면 같은 릴리스를 다시 만들 수 없습니다. 빌드 사이에 main이 바뀌거나 로컬 캐시에 이전 공통 라이브러리가 남아 있을 수 있습니다.

다음 정보만으로는 충분하지 않습니다.

```text
reservation-service: v1.4.0
inventory-service: main
contract-library: 2.3
```

태그가 다른 커밋을 가리키도록 다시 만들어졌거나, `main`이 이동했거나, 로컬 의존성 캐시가 다른 바이너리를 제공할 수 있습니다.

## 계약

### 릴리스 명세에 불변 식별자를 기록합니다

최소한 다음을 고정합니다.

- 저장소 식별자
- 검증된 원격 URL
- commit SHA
- annotated tag와 peeled commit
- 계약 또는 schema 버전
- 빌드 도구와 주요 런타임 버전
- 산출물 digest
- 컨테이너 image digest
- migration 집합
- 생성 시각과 검증 실행 ID

태그와 버전 이름은 사람이 읽기 위한 정보이며, 실제 고정점은 commit과 digest입니다.

### 깨끗한 detached HEAD에서 검증합니다

개발 중인 작업 디렉터리는 수정 파일과 추적되지 않은 파일을 포함할 수 있습니다. 릴리스 검증은 별도 디렉터리에서 수행합니다.

```text
manifest 읽기
→ 각 저장소를 지정 commit으로 checkout
→ detached HEAD 확인
→ tracked/untracked 변경 없음 확인
→ build와 test
→ 산출물 digest 기록
→ build 뒤에도 source tree가 같음 확인
```

검증 도중 생성되는 파일은 source tree 바깥 또는 ignore된 디렉터리에 둡니다. build가 추적 파일을 바꾼다면 재현 가능한 릴리스가 아닙니다.

### 조합의 호환성을 검사합니다

개별 저장소 test가 모두 통과해도 조합이 맞지 않을 수 있습니다.

- 생산자와 소비자의 계약 버전
- DB migration과 이전 application 버전
- 새 서비스와 이전 gateway 설정
- event channel과 schema registry 설정
- image와 환경 변수 이름
- rollback 시 사용할 이전 migration 호환성

manifest는 단순 목록이 아니라 **검증한 조합의 단위**입니다.

### 배포와 rollback도 같은 명세를 사용합니다

배포 도구가 “latest”를 다시 해석하면 검증한 조합과 다른 결과가 실행될 수 있습니다. 배포에는 manifest의 image digest를 사용합니다.

rollback도 이전 manifest를 가리켜야 합니다. 데이터 migration이 되돌릴 수 없는 경우 application만 이전 버전으로 돌릴 수 있는지 미리 검사합니다.

## 실패 조건

- branch 이름이나 움직일 수 있는 tag만 기록합니다.
- lightweight tag를 annotated tag와 같은 근거로 사용합니다.
- 개발 작업 디렉터리에서 릴리스 build를 수행합니다.
- build 전만 source 상태를 확인하고 build 뒤 변경을 확인하지 않습니다.
- 공통 라이브러리를 로컬 Maven cache에서 임의로 가져옵니다.
- 산출물 이름만 기록하고 digest를 남기지 않습니다.
- rollback 조합과 migration 호환성을 검증하지 않습니다.

## 검증

릴리스 검사기는 다음을 명확한 이유로 거절해야 합니다.

- 같은 저장소가 manifest에 두 번 존재합니다.
- 현재 HEAD가 지정 commit과 다릅니다.
- branch가 checkout되어 있습니다.
- 작업 트리가 변경되었거나 untracked 파일이 있습니다.
- tag가 annotated tag가 아닙니다.
- tag를 peel한 commit이 manifest와 다릅니다.

정상 manifest는 임시 Git 저장소에서도 같은 결과를 만들어야 합니다.

## 실습

[release-manifest 실습](../../exercises/04-release-and-evidence/01-release-manifest/README.md)은 실제 임시 Git 저장소를 만들어 detached HEAD, annotated tag와 깨끗한 작업 트리를 검사합니다.

## 완료 조건

- 여러 저장소의 한 릴리스를 commit과 digest로 고정합니다.
- 개발 환경과 릴리스 검증 환경을 분리합니다.
- 조합 호환성과 rollback 가능성을 manifest 단위로 검사합니다.
- 모호한 tag·branch·dirty tree를 자동으로 거절합니다.
