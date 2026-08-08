# 02. 브라우저 기반

## 목표

데이터 연결 전에도 의미 구조, 키보드, URL 상태와 반응형 layout이 검증되는 화면 골격을 만듭니다.

## 구현할 변경

- 로그인, 보드 목록, 보드 화면과 관리 화면의 route 골격을 만듭니다.
- header·nav·main·heading·form·button·label을 의미에 맞게 사용합니다.
- 검색·선택·filter처럼 공유 가능한 상태는 URL에서 읽습니다.
- loading·empty·error·ready 위치를 미리 마련합니다.
- 320px와 확대된 글자에서 줄어들 수 있는 layout을 사용합니다.

## 실패 조건

- 클릭 가능한 `div`가 기본 control을 대신합니다.
- URL과 component state가 같은 값을 각각 소유합니다.
- 색만으로 role·오류·연결 상태를 구분합니다.
- 긴 제목이 viewport 밖으로 밀려납니다.

## 검증

키보드로 주요 화면에 도달하고, 두 번 상태를 바꾼 뒤 뒤로 가기로 이전 화면을 복원하며, 작은 viewport에서 가로 overflow가 없는지 실제 browser로 확인합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:02`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node checks/verify-work.mjs work 2
```

## 완료 계약

API가 아직 없어도 브라우저의 기본 계약과 화면 상태 경계가 독립적으로 검증됩니다.
