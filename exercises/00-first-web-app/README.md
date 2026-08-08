# 첫 웹 애플리케이션: 작업 목록

HTML·CSS·JavaScript를 처음 연결하는 누적 문제입니다. 완성 코드를 먼저 실행하는 대신 `skeleton/`을 복사해 직접 구현하고, 자동 검증을 통과한 뒤 `reference/`와 비교합니다.

## 시작하기

```sh
cd exercises/00-first-web-app
rm -rf work
cp -R skeleton work
node ../../scripts/serve-static.mjs work 8080
```

브라우저에서 `http://127.0.0.1:8080`을 열고 한 단계씩 구현합니다. 다른 터미널에서는 다음 검사를 실행합니다.

```sh
node tests/verify.mjs work
```

검사는 Chrome 또는 Chromium을 실제로 실행합니다. 자동으로 찾지 못하면 실행 파일을 지정합니다.

```sh
CHROMIUM_PATH=/path/to/chromium node tests/verify.mjs work
```

## 구현 순서

1. `index.html`에 본문 건너뛰기 링크, `main`, 제목, 레이블이 있는 폼, 상태 영역과 작업 목록을 만듭니다.
2. `style.css`에 box sizing, 보이는 초점, 좁은 화면 레이아웃과 긴 텍스트 줄바꿈을 추가합니다.
3. 폼 제출 시 공백을 제거한 작업을 추가하고 빈 입력은 거부합니다.
4. 작업 완료 상태와 삭제 동작을 구현합니다.
5. 작업 목록은 `localStorage`에 저장하되, 읽을 때 형식이 잘못되면 안전한 빈 목록으로 복구합니다.
6. 필터는 URL의 `filter` 쿼리를 정본으로 삼고 뒤로 가기에서 화면을 복원합니다.

## 완료 계약

- 마우스 없이 폼, 필터, 완료와 삭제 기능을 사용할 수 있습니다.
- 비어 있는 작업은 추가되지 않고 오류가 `role="alert"`로 전달됩니다.
- 새로 고침해도 작업이 복원됩니다.
- `전체`, `미완료`, `완료` 필터가 URL과 동기화됩니다.
- 뒤로 가기 후 필터와 목록이 함께 복원됩니다.
- 320px 너비에서 가로 스크롤이 생기지 않습니다.
- 사용자 입력을 `innerHTML`에 넣지 않습니다.

## 정답을 확인하는 시점

먼저 `work/`가 모든 검사를 통과하게 만듭니다. 그 뒤에만 다음처럼 차이를 봅니다.

```sh
diff -ru work reference
```

정답과 코드 모양이 달라도 완료 계약을 만족하면 올바른 구현입니다. 차이가 생긴 이유를 설명할 수 있는지가 더 중요합니다.
