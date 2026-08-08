# 05. 문자열

## 목표

KMP의 전처리 상태와 fallback을 표준 검색 및 경계 입력으로 검증한다.

## 구현 대상

- `kmp_find`

## 계약

- 첫 일치 시작 위치를 반환한다.
- 일치가 없으면 `-1`이다.
- 빈 패턴은 0이다.
- Python 문자열 index 단위를 그대로 사용한다.

## 검사 입력

- 빈 본문·빈 패턴
- 패턴이 본문보다 김
- 같은 문자 반복
- 긴 접두사 뒤 실패
- 겹치는 일치
- 고정 시드 짧은 무작위 문자열

## 실행

```sh
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage strings --expect pass
```

`broken/empty-pattern`은 일반 입력에서 맞아 보여도 빈 패턴 계약을 어긴다.

## 완료 기준

- 빈 pattern, 더 긴 pattern, 일치 없음 결과가 Python 검색 계약과 일치한다.
- 반복 문자와 긴 접두사 뒤 mismatch에서 첫 일치 위치를 정확히 반환한다.
- 고정 시드 짧은 문자열 전체에서 표준 `find` 결과와 일치한다.

## 자기 설명

- prefix function의 값이 자기 자신 전체가 아닌 proper prefix 길이여야 하는 이유는 무엇인가?
- mismatch 뒤 이미 확인한 문자를 다시 읽지 않고도 안전하게 fallback할 수 있는 이유는 무엇인가?

## 검증

```sh
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage strings --expect pass
python3 check.py --impl broken/empty-pattern --stage strings --expect fail
```
