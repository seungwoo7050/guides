# 기여 안내

설명과 프로그램은 같은 동작을 가리켜야 합니다. 문서에 적은 명령을 새 작업 디렉터리에서 실행하고, 정상 입력뿐 아니라 오류·경계·경쟁 조건에서도 설명한 상태와 응답이 나오는지 확인합니다.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체로 작성합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 영문 용어는 검색이나 표준 문서 확인에 도움이 될 때 첫 등장에 함께 적습니다.
- 각 장은 `목표 → 실행 모델 또는 계약 → 실패 조건 → 연결 실습 → 완료 기준 → 다음 단계`의 흐름을 따르되, 내용에 맞지 않는 목차를 억지로 반복하지 않습니다.
- 다른 장에서 소유한 개념은 짧게 연결하고 같은 설명을 복사하지 않습니다.
- 테스트로 확인하지 않은 성능·안정성·보안 효과를 단정하지 않습니다.
- 필수 선행지식과 실행 절차는 `docs/` 또는 `exercises/` 안에서 자급되게 합니다.

## 코드를 고칠 때

- 구현 문제는 `exercises` 아래에 `skeleton`, 자동 검사와 `reference`를 함께 둡니다.
- 기본 학습 순서는 `pnpm workspace:create <exercise> → work/ 직접 구현 → 검사 통과 → reference 비교`입니다. canonical `skeleton/`과 `reference/`를 직접 수정해 학습하지 않습니다.
- `skeleton`은 구현할 경계를 드러내고, `reference`에는 `TODO`, 임시 반환값이나 비활성 검사를 남기지 않습니다.
- 검사기는 정답 파일의 문구나 소스 배치보다 실제 입력·출력·상태 전이를 확인합니다.
- 브라우저·서버·socket·timer·DB pool과 임시 파일은 성공과 실패 경로 모두에서 정리합니다.
- 고정 sleep보다 관찰 가능한 상태를 기다리고, 검사마다 고유 데이터와 빈 port를 사용합니다.
- 비밀번호, 인증서, 빌드 결과와 실행 중 생성된 보고서는 추적하지 않습니다.

## 변경 확인

먼저 의존성 없이 실행되는 구조 검사를 수행합니다.

```sh
pnpm check:repository
```

초기 브라우저 실습은 실제 Chrome 또는 Chromium으로 확인합니다.

```sh
pnpm verify:foundations
```

의존성, PostgreSQL과 브라우저를 준비한 환경에서는 전체 검증을 수행합니다.

```sh
pnpm install --frozen-lockfile
pnpm --dir exercises/08-testing/reference exec playwright install chromium
pnpm --dir exercises/collaboration-board/reference exec playwright install chromium
pnpm verify
```

실습 계약과 검사기의 결함 검출력만 다시 확인할 때는 같은 환경에서 `pnpm check`를 실행합니다.

누적 patch는 실제 Git history가 아니라 source에서 파생한 curated 권장 구현 순서 walkthrough입니다. patch 무결성과 freshness만 확인하려면 다음 명령을 사용합니다.

```sh
pnpm check:walkthrough
```

커밋 전에는 추적 범위와 공백 오류를 다시 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 커밋

제목은 Conventional Commits 형식을 사용하고, 문서와 그 계약을 검증하는 코드는 같은 변경에 포함할 수 있습니다.

```text
docs(web): URL 상태 복원 계약 보완
test(browser): 뒤로 가기와 320px 검증 추가
fix(auth): 로그아웃 시 서버 세션 폐기
```
