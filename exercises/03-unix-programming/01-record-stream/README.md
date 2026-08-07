# 연습문제: record-stream

## 목표

파일 디스크립터에서 newline 구분 레코드를 한 개씩 반환하는 상태형 reader를 구현합니다. 부분 읽기, 빈 레코드, EOF, 포함된 NUL과 할당 실패 뒤 상태를 구분합니다.

## 구현 위치

`skeleton/src/record_stream.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

## 반환 계약

```text
1   레코드를 반환함
0   EOF이며 남은 레코드가 없음
-1  잘못된 인자, I/O 또는 메모리 오류
```

- 성공 1이면 `*out_record`는 호출자가 `free`할 독립 할당이고 `*out_length`는 실제 바이트 수입니다.
- 반환 0 또는 -1에서는 출력 매개변수를 변경하지 않습니다.
- newline은 반환 데이터에 포함하지 않습니다.
- 연속 newline은 길이 0인 레코드를 만듭니다.
- newline 없이 끝난 마지막 비어 있지 않은 레코드를 반환합니다.
- 포함된 NUL도 길이와 바이트 배열로 보존합니다. `%s`나 `strlen`만으로 검사하지 않습니다.
- `init`은 아직 초기화되지 않은 reader에 호출합니다. 내부 buffer가 남은 reader를 다시 초기화하지 않습니다.
- reader의 공개 필드는 `init` 뒤 직접 변경하지 않습니다.
- reader는 fd를 빌리며 destroy가 fd를 닫지 않습니다. destroy 뒤 다시 읽으려면 `init`을 다시 호출합니다.
- 서로 다른 reader는 내부 상태를 공유하지 않습니다.
- 내부 buffer 할당 실패 뒤 reader는 terminal 실패 상태가 되고 이후 호출도 -1입니다.
- EOF는 반복 호출해도 계속 0이며 이전 출력 값을 덮지 않습니다.

## 검증

```sh
make exercise-test
make sanitize
```

검사는 청크 크기 1, 여러 청크에 걸친 긴 레코드, 빈 레코드, 마지막 조각, 반복 EOF, 포함된 NUL, 두 reader의 교차 호출, borrowed FD 수명과 내부 할당 실패를 확인합니다.
