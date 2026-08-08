# 오류·optional·variant·expected

## 목표

모든 실패를 예외로 던지거나 모든 함수를 `bool`로 만들지 않습니다. 실패의 의미와 caller가 취할 행동에 따라 다음을 구분합니다.

- programmer error와 깨진 precondition
- 값이 없을 수 있는 정상 분기
- 예상 가능한 업무 거부
- 외부 시스템과 자원 실패
- 현재 계층에서 복구할 수 없는 예외적 실패

오류 표현은 문법 선택이 아니라 API 계약입니다.

## 시작하기 전에

[클래스·책임·다형성](04-classes-responsibilities-and-polymorphism.md)을 완료하고 어느 객체가 상태를 변경하는지 설명할 수 있어야 합니다.

## 1. 먼저 실패를 분류합니다

### programmer error

호출자가 API 계약을 어긴 경우입니다.

```cpp
char& Buffer::operator[](std::size_t index)
{
    assert(index < size());
    return data_[index];
}
```

`operator[]`처럼 precondition을 요구하는 낮은 수준 연산의 내부 가정을 검사한 예입니다. 범위 검사가 공개 계약인 `at`류 API라면 예외나 결과 타입으로 실패를 보고해야 합니다. 공개 입력에서 발생할 수 있는 오류를 assertion으로만 처리하면 Release에서 검사가 사라질 수 있습니다. assertion은 내부 불변식과 개발 중 가정 검사에 사용합니다.

### 정상적인 부재

조회 결과가 없을 수 있습니다.

```cpp
std::optional<Job> find(JobId id) const;
```

없음은 오류 메시지나 stack trace가 필요한 사건이 아닐 수 있습니다.

### 예상 가능한 거부

queue가 가득 찼거나 권한이 부족한 경우 caller가 분기해야 합니다.

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

메모리 부족, invariant 파괴, filesystem I/O 실패처럼 현재 함수가 정상 결과로 처리하기 어려운 실패입니다. 예외를 사용할 수 있지만 어느 계층에서 잡고 번역할지 정해야 합니다.

## 2. `optional<T>`

값 하나가 있거나 없는 경우 적합합니다.

```cpp
std::optional<TaskId> parse_id(std::string_view text);
```

다음 정보가 필요하면 optional만으로 부족합니다.

- 어떤 입력 위치에서 실패했는가
- 형식 오류와 범위 초과를 구분하는가
- caller에게 보여 줄 메시지가 필요한가

그때는 오류 타입을 가진 결과를 사용합니다.

## 3. `variant`로 닫힌 결과 집합 표현

C++20에서는 `std::variant<T, E>`를 작은 result 경계로 사용할 수 있습니다.

```cpp
using ParseResult = std::variant<Command, ParseError>;
```

caller는 활성 타입을 명시적으로 확인합니다.

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

성공과 실패 타입이 여러 곳에서 반복되면 작은 `Result<T, E>` wrapper로 `has_value`, `value`, `error` 계약을 모을 수 있습니다. 단, 표준 `expected`와 다른 자체 타입의 의미를 문서화해야 합니다.

## 4. `std::expected`

`std::expected<T, E>`는 C++23 표준 라이브러리 기능입니다. 사용할 수 있는 환경에서는 성공값과 예상 가능한 오류를 직접 표현합니다.

```cpp
std::expected<JobId, SubmitError> submit(JobSpec spec);
```

이 저장소의 필수 기준은 C++20이므로 reference exercise는 작은 `Result<T, E>`를 사용합니다. 프로젝트 기준이 C++23 이상이면 자체 wrapper를 유지하기보다 표준 `expected`로 교체하는 것이 일반적으로 낫습니다.

## 5. 예외를 사용할 조건

예외는 다음 조건에서 유용합니다.

- 정상 호출 코드에서 실패 분기를 계속 전달할 필요가 없습니다.
- 현재 계층이 복구할 수 없고 상위 경계가 처리합니다.
- RAII로 중간 자원이 안전하게 정리됩니다.
- library와 애플리케이션의 예외 정책이 일치합니다.

예:

```cpp
std::string read_required_config(const std::filesystem::path& path);
```

필수 설정 파일을 읽지 못하면 application startup을 중단하는 예외가 합리적일 수 있습니다.

반면 queue full은 정상적인 backpressure 분기이므로 매번 예외로 던지기보다 값 오류가 더 명확합니다.

## 6. 예외 경계

예외가 thread 함수, callback ABI, process main 밖으로 빠져나가지 않도록 경계를 둡니다.

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

모든 함수에서 잡았다가 다시 던지는 것은 의미가 없습니다. 다음 중 하나를 할 수 있는 경계에서 잡습니다.

- 복구
- retry 여부 결정
- 오류 타입 번역
- context 추가
- process 또는 request 응답으로 변환

## 7. 예외 안전성 보장

함수가 실패했을 때 객체 상태에 대해 다음 수준을 구분합니다.

- no-throw guarantee: 실패를 밖으로 던지지 않습니다.
- strong guarantee: 실패하면 관찰 가능한 상태가 호출 전과 같습니다.
- basic guarantee: 불변식과 자원 안전은 유지되지만 값은 바뀔 수 있습니다.
- no guarantee: 객체 상태를 신뢰할 수 없습니다.

container 갱신에서는 임시값에 먼저 작업한 뒤 commit하면 strong guarantee를 만들 수 있습니다.

```cpp
void replace_config(Config next)
{
    validate(next);       // 기존 상태 변경 전 실패 가능
    config_.swap(next);   // Config::swap이 noexcept인 commit
}
```

임시값을 만들었다는 사실만으로 strong guarantee가 생기지는 않습니다. 최종 commit 연산도 실패하지 않아야 합니다. move assignment가 중간에 예외를 던질 수 있다면 해당 대입만으로 호출 전 상태를 보장할 수 없습니다.

여러 외부 효과가 섞이면 메모리 객체의 strong guarantee만으로 전체 업무 rollback이 되지 않습니다.

## 8. 오류 타입 설계

오류 문자열 하나에 모든 의미를 넣지 않습니다.

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

기계적 분기와 사람이 읽을 메시지를 분리합니다. 메시지 문구가 바뀌어도 caller의 분기 계약이 깨지지 않습니다.

## 9. `std::error_code`와 시스템 오류

filesystem과 C API 오류는 `std::error_code`로 보존할 수 있습니다.

```cpp
std::error_code error;
const bool removed = std::filesystem::remove(path, error);
if (error)
{
    // error.value(), error.category(), error.message()
}
```

exception overload와 error-code overload 중 하나를 의도적으로 선택합니다.

- 현재 계층이 실패를 값으로 조합해야 하면 error code가 편리합니다.
- 실패 시 정상 흐름을 중단하고 상위 경계가 처리하면 exception overload가 간단할 수 있습니다.

둘을 섞어 같은 오류를 두 번 보고하지 않습니다.

## 10. 오류 번역

낮은 수준 오류를 그대로 모든 계층에 노출하지 않습니다.

```text
filesystem permission denied
→ ConfigLoadError{code=unreadable, path=...}
→ startup diagnostic
→ process exit
```

번역할 때 원인을 잃지 않습니다. `std::nested_exception`, 원본 `error_code`, 경로와 작업 이름을 보존할 수 있습니다.

## 11. 실패 뒤 출력 parameter

```cpp
bool parse(std::string_view text, Config& output);
```

이 API는 실패 뒤 `output` 상태를 정해야 합니다.

- 변경되지 않음
- 초기값으로 바뀜
- 부분 결과를 가짐

명확한 이유가 없다면 임시 객체에 parsing한 뒤 성공 시 대입해 기존 값을 유지하는 편이 좋습니다. 또는 `Result<Config, ParseError>`를 반환해 상태를 분리합니다.

## 12. destructor와 오류

소멸자에서 예외를 던지지 않는 것을 기본으로 합니다. flush·commit 성공이 중요하면 명시적 함수에서 검사합니다.

```cpp
writer.finish(); // 오류 보고 가능
// destructor는 남은 자원을 정리
```

“RAII가 정리한다”와 “업무 결과가 영구 저장됐다”는 다른 보장입니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)에서 다음 경계를 구현합니다.

- 빈 이름·빈 callable·queue full·종료됨: `SubmitError` 값
- 존재하지 않는 job 조회: `optional`
- 작업 callable의 예외: worker 경계에서 `failed` 상태로 번역
- journal을 처음 열 수 없음: 생성 실패 예외
- 생성 뒤 append 실패: 작업 상태와 분리된 health 값
- stop과 cancel: 상태 전이, 예외가 아님

같은 “실패”라는 단어가 서로 다른 표현을 갖는 이유를 설명합니다.

## 실패 실험

- 모든 submit 거부를 `runtime_error`로 바꿉니다.
- 모든 parsing 실패를 빈 optional 하나로 합칩니다.
- worker callable 예외를 잡지 않습니다.
- 출력 parameter를 절반 수정한 뒤 false를 반환합니다.
- destructor에서 flush 예외를 던집니다.

## 완료 기준

- programmer error, 부재, 예상 가능한 거부와 예외적 실패를 구분합니다.
- `optional`, result/`variant`, exception과 `error_code`를 목적에 맞게 선택합니다.
- 예외를 잡을 번역 경계를 설명합니다.
- 실패 뒤 상태 보장 수준을 문서화합니다.
- C++20 기준과 C++23 `expected` 선택을 구분합니다.

## 다음 문서

[알고리즘·ranges·templates·concepts](06-algorithms-ranges-templates-and-concepts.md)에서 값과 오류 계약을 여러 container와 타입에 재사용하는 방법을 다룹니다.
