# Exercise 02 — Lexer, parser와 AST

## 목표

Mica source를 token과 AST로 바꾸고 precedence·recovery·source span 계약을 검증합니다.

## 과제

### 1. Token table

각 token에 다음을 적습니다.

- lexeme 또는 pattern
- longest-match 충돌
- literal decode
- trivia 처리
- 오류 code

필수 case:

```text
= / ==
< / <=
identifier / keyword
- / negative literal
string escape
line comment
CRLF
EOF
```

### 2. Lexer progress

모든 loop가 token 생성, cursor 전진 또는 EOF 종료 중 하나를 수행하는지 확인합니다. Invalid byte/character fixture가 hang하지 않아야 합니다.

### 3. Statement parser

Recursive descent로 function, block, declaration, if, while, return을 만듭니다. 각 parse function의 synchronization token을 기록합니다.

### 4. Pratt parser

Mica operator의 binding power table을 하나의 정본으로 둡니다.

필수 구조:

```text
1 + 2 * 3
1 - 2 - 3
!a == b
f(1)(2)  # function value 확장 시
(a + b) * c
```

### 5. AST dump

- stable kind 이름
- half-open span
- 명시적 child field
- literal value와 raw span 구분
- `ErrorExpr`/`ErrorStmt`
- pointer/address 제외

## Recovery case

- missing `;`
- missing `)`
- missing `}` at EOF
- unexpected operator
- invalid statement token
- function 뒤 다음 function까지 synchronization

Recovery 뒤 parser가 같은 token에서 반복 실패하지 않아야 합니다.

## Known-bad

`+`의 precedence를 `*`보다 높게 바꾸거나, missing `;`에서 token을 전진시키지 않는 변형을 만듭니다. 구조 test 또는 timeout이 거부해야 합니다.

## 제출

- grammar→parse function 대응표
- binding power table
- token/AST schema
- 정상 fixture 5개, recovery fixture 5개
- normalized AST dump
- parser 종료를 확인하는 random token smoke test

## 완료 기준

모든 AST node span이 source 범위 안에 있고, precedence fixture가 명세대로 구조화되며, 잘못된 입력이 diagnostic을 남기고 제한 시간 안에 EOF 또는 synchronization 지점으로 진행합니다.
