# 브라우저 UI: 의미 구조, URL 상태와 반응형 화면

의미가 있는 검색 폼을 만들고, 검색 조건을 URL에 저장하며, 키보드·뒤로 가기·작은 화면을 실제 Chromium으로 검증합니다.

## 선행 문서

- [`HTML 폼과 접근성`](../../docs/01-web-foundations/02-html-forms-accessibility.md)
- [`CSS 레이아웃과 반응형 화면`](../../docs/01-web-foundations/03-css-layout-responsive.md)
- [`DOM, 이벤트, URL과 저장소`](../../docs/01-web-foundations/05-dom-events-url-storage.md)

## 작업하기

```sh
cd exercises/02-browser
rm -rf work
cp -R skeleton work
node tests/verify.mjs work
```

검사는 완성 전에는 실패하는 것이 정상입니다. 실패 메시지를 한 항목씩 줄이며 구현합니다. Chrome이나 Chromium을 찾지 못하면 `CHROMIUM_PATH`를 지정합니다.

## 구현할 계약

- `header`, 이름 있는 `nav`, `main`, 제목 계층과 `role="search"` 폼을 사용합니다.
- 입력에는 실제 `label`을 연결하고 상태는 `role="status"`로 알립니다.
- 검색 제출은 `history.pushState`로 `q` 쿼리를 갱신합니다.
- `popstate`에서는 메모리 값이 아니라 현재 URL을 다시 읽습니다.
- 검색 결과의 사용자 문자열은 `textContent`로 출력합니다.
- 첫 Tab에서 본문 건너뛰기 링크가 나타납니다.
- 320px에서도 가로 overflow가 생기지 않습니다.

## 자동 검증

```sh
node tests/verify.mjs work
```

이 검사는 정적 문자열 존재 여부로 끝나지 않습니다. 실제 브라우저에서 두 검색을 수행하고 뒤로 가기로 이전 검색을 복원하며, 키보드 초점과 viewport overflow를 확인합니다.

## 실패 주입

- `button`을 클릭 가능한 `div`로 바꿉니다.
- `label`을 시각적 텍스트만 남기고 연결을 끊습니다.
- `popstate` 수신기를 제거합니다.
- URL과 별도의 전역 검색 상태를 정본으로 만듭니다.
- 결과를 `innerHTML`에 연결합니다.

## 완료 기준

자동 검증이 통과하고, 각 실패 주입이 어떤 사용자 계약을 깨는지 설명할 수 있어야 합니다. 그 뒤에만 `reference/`와 비교합니다.
