# Exercise 01 — Source와 diagnostic

## 목표

Source text를 단순 문자열이 아니라 version이 있는 snapshot으로 다루고, UTF-8 byte span을 안정적인 diagnostic JSON과 text renderer로 변환합니다.

## 과제

### 1. SourceSnapshot

다음을 구현하거나 설계합니다.

```text
SourceId
version
UTF-8 bytes
line start offsets
path/display name
```

필수 invariant:

- source bytes는 snapshot lifetime 동안 바뀌지 않습니다.
- span은 같은 SourceId 안의 half-open range입니다.
- `0 <= start <= end <= byte_length`입니다.

### 2. 위치 변환

- byte offset → zero-based line
- byte offset → one-based human line/column
- byte span → renderer underline
- UTF-16 position adapter의 설계 또는 구현

입력 case:

```text
ASCII
한글
non-BMP emoji
LF
CRLF
tab
EOF zero-width span
```

### 3. Diagnostic

최소 field:

```text
schema_version
code
severity
message
phase
primary span
secondary labels
notes
```

Message text보다 code와 span을 test합니다.

### 4. Renderer

- source line과 caret
- multiline span 정책
- tab display policy
- source line이 매우 긴 경우 clipping
- stale source version 거부

[`examples/diagnostic-renderer`](../../examples/diagnostic-renderer/README.md)는 작은 관찰 예제입니다. 그대로 복사하지 않고 span 단위와 renderer 정책을 먼저 결정합니다.

## 실패 case

- start > end
- end가 source length보다 큼
- 다른 SourceId span merge
- UTF-8 byte를 code point index로 slice
- version 1 diagnostic을 version 2 source에 적용
- invalid UTF-8 정책 미정

## Known-bad

의도적으로 emoji 앞 byte offset을 character column으로 출력하는 변형을 만들고 test가 거부하는지 확인합니다.

## 제출

- `CONTRACT.md`
- source/span/line map 구현 또는 상세 pseudocode
- diagnostic JSON schema
- 정상·실패 fixture 8개 이상
- renderer output 3개
- 자동 검사의 한계

## 완료 기준

같은 snapshot과 diagnostic을 반복 처리하면 byte-for-byte 같은 JSON이 나오고, 모든 primary/secondary span이 source 범위 안에 있으며 Unicode case에서 caret가 의도한 token을 가리킵니다.
