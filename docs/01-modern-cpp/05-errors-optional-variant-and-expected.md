# 오류·optional·variant·expected

## 목표

모든 실패에 예외를 사용하거나 모든 함수가 `bool`을 반환하게 만들지 않습니다. 실패의 의미와 호출자가 취해야 할 행동에 따라 다음 경우를 구분합니다.

- 프로그래머 오류와 위반된 사전 조건
- 값이 없을 수 있는 정상적인 분기
- 예상 가능한 요청 거부
- 외부 시스템과 자원에서 발생한 오류
- 현재 계층에서 복구할 수 없는 예외적 실패

오류 표현 방식은 문법상의 선택이 아니라 API의 동작 계약입니다.

## 시작하기 전에

[클래스·책임·다형성](04-classes-responsibilities-and-polymorphism.md)을 완료하고 어느 객체가 상태 변경을 책임지는지 설명할 수 있어야 합니다.

## 1. 실패의 종류부터 분류합니다

### 프로그래머 오류

호출자가 API의 사전 조건을 어긴 경우입니다.

```cpp
char& Buffer::operator[](std::size_t index)
{
    assert(index < size());
    return data_[index];
}
```

`operator[]`처럼 범위가 유효하다는 사전 조건을 요구하는 저수준 연산에서 내부 가정을 검사한 예입니다. 범위 검사가 공개 기능인 `at` 계열 API라면 예외나 결과 타입으로 실패를 보고해야 합니다. 외부 입력으로 발생할 수 있는 오류를 assertion에만 맡기면 `NDEBUG`가 정의된 빌드에서 검사가 제거될 수 있습니다. assertion은 내부 불변식과 개발 중 가정 검증에 사용합니다.

### 정상적인 부재

조회 대상이 존재하지 않는 것이 정상 흐름일 수 있습니다.

```cpp
std::optional<Job> find(JobId id) const;
```

이 경우 값이 없다는 사실에 오류 메시지나 스택 추적이 필요하지 않을 수 있습니다.

### 예상 가능한 거부

큐가 가득 찼거나 권한이 부족해 호출자가 별도 분기를 수행해야 하는 경우입니다.

```cpp
enum class SubmitError
{
    stopped,
    queue_full,
    empty_name,
    empty_work
};

Result<JobId, SubmitError> submit(JobSpec spec);
```

### 예외적 실패

메모리 할당 실패, 불변식 훼손, 파일 시스템 I/O 오류처럼 현재 함수의 정상 결과로 처리하기 어려운 실패입니다. 예외를 사용할 수 있지만 어느 계층에서 잡고 도메인 오류나 사용자 진단으로 변환할지 정해야 합니다.

## 2. `optional<T>`

값 하나가 존재하거나 존재하지 않는 경우에 적합합니다.

```cpp
std::optional<TaskId> parse_id(std::string_view text);
```

다음 정보가 필요하다면 `optional`만으로는 부족합니다.

- 입력의 어느 위치에서 실패했는가
- 형식 오류와 범위 초과를 구분해야 하는가
- 호출자에게 보여 줄 오류 메시지가 필요한가

이때는 별도 오류 타입을 포함한 결과를 사용합니다.

## 3. `variant`로 닫힌 결과 집합 표현

C++20에서는 `std::variant<T, E>`를 간단한 결과 타입으로 사용할 수 있습니다.

```cpp
using ParseResult = std::variant<Command, ParseError>;
```

호출자는 현재 활성화된 대안을 명시적으로 확인합니다.

```cpp
if (const auto* command = std::get_if<Command>(&result))
{
    execute(*command);
}
else
{
    report(std::get<ParseError>(result));
}
```

같은 성공·실패 형태가 여러 곳에서 반복되면 작은 `Result<T, E>` 래퍼로 `has_value`, `value`, `error` 인터페이스를 모을 수 있습니다. 자체 결과 타입을 만든다면 표준 `expected`와 다른 동작, 잘못된 대안 접근 방식, 값과 오류의 생성 규칙을 문서화해야 합니다.

## 4. `std::expected`

`std::expected<T, E>`는 C++23 표준 라이브러리에 추가된 기능으로, 성공값 또는 예상 가능한 오류를 직접 표현합니다.

```cpp
std::expected<JobId, SubmitError> submit(JobSpec spec);
```

이 저장소의 필수 기준은 C++20이므로 참조 실습에서는 작은 `Result<T, E>`를 사용합니다. 프로젝트가 C++23 이상을 기준으로 하고 사용하는 표준 라이브러리가 `std::expected`를 지원한다면 자체 래퍼를 유지할 이유가 있는지 다시 검토합니다.

## 5. 예외를 사용할 조건

예외는 다음 조건에서 유용할 수 있습니다.

- 일반 호출 코드의 모든 단계에서 실패값을 반복해 전달하고 싶지 않습니다.
- 현재 계층은 복구할 수 없지만 상위 경계에서 처리할 수 있습니다.
- RAII로 중간에 획득한 자원이 안전하게 정리됩니다.
- 라이브러리와 애플리케이션의 예외 정책이 일치합니다.

예를 들어 다음 함수가 읽는 설정 파일이 애플리케이션 시작에 반드시 필요하다면, 읽기 실패를 예외로 보고하고 시작 경계에서 진단한 뒤 종료하는 정책이 합리적일 수 있습니다.

```cpp
std::string read_required_config(const std::filesystem::path& path);
```

반면 큐 포화는 정상적인 백프레셔(backpressure) 분기이므로 매번 예외를 던지기보다 오류값으로 반환하는 편이 명확합니다.

## 6. 예외 경계

예외가 스레드 진입 함수, C 콜백 경계, `main` 바깥으로 전파되지 않게 처리 지점을 둡니다.

```cpp
void worker_loop()
{
    try
    {
        run_job();
    }
    catch (const std::exception& exception)
    {
        mark_failed(exception.what());
    }
    catch (...)
    {
        mark_failed("unknown exception");
    }
}
```

모든 함수에서 예외를 잡은 뒤 아무 처리 없이 다시 던질 필요는 없습니다. 다음 중 하나를 수행할 수 있는 경계에서 잡습니다.

- 복구
- 재시도 여부 결정
- 더 상위 수준의 오류 타입으로 변환
- 진단에 필요한 문맥 추가
- 프로세스 종료 상태나 요청 응답으로 변환

## 7. 예외 안전성 보장

함수가 실패했을 때 객체 상태에 대해 다음 수준을 구분합니다.

- 무예외 보장: 연산이 예외를 밖으로 내보내지 않습니다.
- 강한 예외 보장: 실패하면 관찰 가능한 상태가 호출 전과 같습니다.
- 기본 예외 보장: 불변식과 자원 안전은 유지되지만 일부 값은 바뀔 수 있습니다.
- 보장 없음: 실패 후 객체 상태에 유용한 보장이 없습니다.

컨테이너나 설정을 변경할 때 새 값을 임시 객체에서 먼저 준비한 뒤 한 번에 반영하면 강한 보장을 만들 수 있습니다.

```cpp
void replace_config(Config next)
{
    validate(next);       // 기존 상태를 바꾸기 전에 실패 가능
    config_.swap(next);   // Config::swap이 noexcept인 반영 단계
}
```

임시 객체를 사용했다는 사실만으로 강한 보장이 생기지는 않습니다. 마지막 반영 연산도 실패하지 않아야 합니다. 이동 대입 중 예외가 발생할 수 있다면 단순 대입만으로 호출 전 상태 복원을 보장할 수 없습니다.

또한 파일 쓰기나 네트워크 전송 같은 외부 효과가 섞이면 메모리 객체에 대한 강한 예외 보장만으로 전체 작업이 롤백되지는 않습니다.

## 8. 오류 타입 설계

하나의 오류 문자열에 모든 의미를 넣지 않습니다.

```cpp
enum class ParseCode
{
    empty,
    invalid_number,
    out_of_range,
    unknown_command
};

struct ParseError
{
    ParseCode code;
    std::size_t offset;
    std::string input;
};
```

프로그램이 분기할 오류 코드와 사람이 읽을 메시지를 분리합니다. 메시지 문구가 바뀌어도 호출자의 제어 흐름이 깨지지 않아야 합니다.

## 9. `std::error_code`와 시스템 오류

파일 시스템과 C API에서 발생한 오류를 `std::error_code`로 보존할 수 있습니다.

```cpp
std::error_code error;
const bool removed = std::filesystem::remove(path, error);
if (error)
{
    // error.value(), error.category(), error.message()
}
```

예외를 던지는 오버로드와 `error_code`를 받는 오버로드 중 하나를 의도적으로 선택합니다.

- 현재 계층이 여러 실패를 값으로 조합해야 한다면 `error_code` 방식이 편리할 수 있습니다.
- 실패 시 정상 흐름을 중단하고 상위 경계에서 처리한다면 예외 오버로드가 단순할 수 있습니다.

두 방식을 섞어 같은 오류를 중복 보고하지 않습니다.

## 10. 오류 번역

저수준 오류를 모든 계층에 그대로 노출하지 않습니다.

```text
파일 시스템 권한 오류
→ ConfigLoadError{code=unreadable, path=...}
→ 시작 실패 진단
→ 프로세스 종료
```

상위 오류로 변환하더라도 원인을 잃지 않습니다. 원본 `error_code`, 작업 경로, 수행한 연산, 필요한 경우 중첩 예외를 보존할 수 있습니다.

## 11. 실패 후 출력 매개변수 상태

```cpp
bool parse(std::string_view text, Config& output);
```

이 인터페이스는 실패 후 `output`이 어떤 상태인지 정해야 합니다.

- 호출 전 값이 유지됨
- 초기값으로 바뀜
- 유효한 부분 결과를 가짐

특별한 이유가 없다면 임시 객체에 파싱한 뒤 성공했을 때만 대입해 기존 값을 유지하는 편이 명확합니다. 또는 `Result<Config, ParseError>`를 반환해 성공값과 오류를 분리합니다.

## 12. 소멸자와 오류

소멸자에서 예외를 내보내지 않는 것을 기본으로 합니다. `flush`나 `commit`의 성공 여부가 중요하다면 명시적인 함수에서 결과를 검사합니다.

```cpp
writer.finish(); // 오류를 보고할 수 있음
// 소멸자는 남은 자원을 정리
```

RAII가 자원을 정리한다는 보장과 업무 결과가 영구 저장됐다는 보장은 서로 다릅니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)에서 다음 오류 경계를 구현합니다.

- 빈 이름·비어 있는 호출 가능 객체·큐 포화·실행기 종료: `SubmitError` 값
- 존재하지 않는 작업 조회: `optional`
- 작업 함수의 예외: 워커 경계에서 `failed` 상태로 변환
- 저널을 처음 열 수 없음: 생성 실패 예외
- 생성 후 추가 기록 실패: 작업 상태와 분리된 저널 기록 상태
- `stop`과 `cancel`: 상태 전이 결과이며 예외가 아님

모두 실패로 부를 수 있지만 서로 다른 표현이 필요한 이유를 설명합니다.

## 실패 실험

- 모든 작업 제출 거부를 `runtime_error`로 바꿉니다.
- 모든 파싱 실패를 빈 `optional` 하나로 합칩니다.
- 작업 함수에서 나온 예외를 워커 경계에서 잡지 않습니다.
- 출력 매개변수를 일부 수정한 뒤 `false`를 반환합니다.
- 소멸자에서 `flush` 예외를 던집니다.

## 완료 기준

- 프로그래머 오류, 정상적인 부재, 예상 가능한 거부, 예외적 실패를 구분합니다.
- `optional`, 결과 타입/`variant`, 예외, `error_code`를 목적에 맞게 선택합니다.
- 예외를 잡아 번역해야 하는 경계를 설명합니다.
- 실패 후 상태 보장 수준을 문서화합니다.
- C++20 자체 결과 타입과 C++23 `std::expected`의 선택 조건을 구분합니다.

## 다음 문서

[알고리즘·ranges·templates·concepts](06-algorithms-ranges-templates-and-concepts.md)에서 값과 오류 규칙을 여러 컨테이너와 타입에 재사용하는 방법을 다룹니다.
