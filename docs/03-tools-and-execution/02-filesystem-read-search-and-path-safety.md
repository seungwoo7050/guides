# Filesystem read·search와 경로 안전성

## 목표

코딩 에이전트가 필요한 파일을 읽고 검색하면서 workspace 밖으로 이탈하거나 대용량·binary·symlink·특수 파일 때문에 경계를 잃지 않게 합니다.

## path는 문자열이 아니다

입력 path를 다음 순서로 처리합니다.

1. encoding과 null byte를 검사합니다.
2. workspace root 기준으로 해석합니다.
3. `.`·`..`와 separator를 정규화합니다.
4. symlink를 포함한 실제 target을 확인합니다.
5. canonical target이 허용 root 안인지 검사합니다.
6. file type과 permission을 검사합니다.
7. resource grant의 read/write pattern을 적용합니다.

lexical prefix 검사만으로는 `../`, symlink, case normalization과 mount 경계를 막지 못합니다.

## 읽기 계약

`read_file` 결과 예시:

```text
canonical_path
file_type
size
mode
encoding
content_or_excerpt
content_digest
line_range
truncated
repository_snapshot_id
```

대용량 file은 offset·line range 또는 bounded excerpt를 사용합니다. 같은 file을 여러 chunk로 읽으면 digest가 같은지 확인합니다.

## file type 정책

### 일반 text

encoding과 newline을 보존합니다.

### binary

기본적으로 metadata만 반환하고 명시적 binary tool이나 hex 제한을 사용합니다.

### symlink

link 자체를 읽는 것과 target content를 읽는 것을 구분합니다. write는 target과 link 교체를 별도 action으로 취급합니다.

### device·socket·FIFO

일반 file tool에서 거절합니다. 읽기가 block되거나 외부 process와 상호작용할 수 있습니다.

### generated·vendor·cache

검색에서 기본 제외하되 task와 build manifest가 필요성을 보이면 명시적으로 포함합니다.

## directory listing

전체 재귀 tree를 한 번에 반환하지 않습니다.

```text
path
depth
max_entries
include_hidden
include_ignored
file_type filter
```

결과는 deterministic order와 truncation cursor를 가져야 합니다.

## text search

`search_text`는 다음을 통제합니다.

- query kind: literal·regex
- path scope
- ignored/generated 정책
- binary 처리
- match count와 file count 상한
- context line 수
- timeout
- result ordering

정규식 catastrophic backtracking과 shell interpolation을 피합니다. 가능한 경우 검증된 search executable을 argv로 실행하거나 library를 사용합니다.

## 읽기와 permission

읽기 전용이라고 항상 무해하지 않습니다.

- home directory의 credential
- `.env`, key, token cache
- 다른 repository
- hidden test와 answer fixture
- verifier source
- user private file

workspace 안에서도 deny list와 sensitive classification을 둘 수 있습니다. secret file을 모델 context로 보내지 않고 필요한 metadata 또는 redacted value만 tool에서 처리합니다.

## TOCTOU

permission check 뒤 file이 symlink로 바뀔 수 있습니다. 강한 경계가 필요하면 다음을 고려합니다.

- directory file descriptor 기준 open
- no-follow option
- open 후 실제 inode·path 확인
- sandbox mount를 read-only로 고정
- snapshot filesystem

문서 수준에서는 위협 모델에 따라 어떤 강도를 선택했는지 명시합니다.

## 실패 조건

- `startswith(workspace_root)`로 path 허용을 판정합니다.
- symlink target을 확인하지 않습니다.
- 검색 결과가 hidden verifier나 answer file을 포함합니다.
- 대형 log를 전체 context에 넣습니다.
- read-only permission이 home·credential·other repo까지 열려 있습니다.
- file이 읽는 동안 바뀌어도 digest 없이 사용합니다.

## 완료 조건

- path traversal, symlink escape, case 차이와 special file을 거절하는 설계를 제시합니다.
- read result가 content digest와 snapshot identity를 가집니다.
- secret·hidden evaluation resource와 일반 source를 분리합니다.
- large file과 search result에 시간·크기·개수 한도가 있습니다.
