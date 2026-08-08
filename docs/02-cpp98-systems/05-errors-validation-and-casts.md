# 오류 처리, 입력 검증과 타입 경계

## 실패도 인터페이스의 일부입니다

모든 실패를 `false`나 문자열 하나로 처리하면 호출자는 무엇을 복구할 수 있는지 알 수 없습니다. 반대로 모든 문제에 예외를 던지면 정상적인 분기까지 숨은 제어 흐름이 됩니다. 실패의 종류와 처리 책임을 구분하고, 입력 변환부터 상태 반영까지 각 단계가 보장할 조건을 확인합니다.

## 입력에서 오류 응답까지

```text
raw input → 문법 검증 → 타입 변환 → 도메인 검증 → 상태 변경
    실패 A      실패 B       실패 C          실패 D
                                      ↓
                              애플리케이션 경계
                                      ↓
                              외부 오류 표현
```

캐스트는 변환만 수행합니다. 범위·수명·실제 타입 검증은 별도 단계입니다.

## 오류 경로를 코드로 검증

`../exercises/02-cpp98-systems/object-model/command-service/05-errors`는 파서 오류, 도메인 오류와 최상위 응답 변환을 분리합니다.

```sh
cd ../exercises/02-cpp98-systems/object-model/command-service/05-errors
make observe
make exercise-test
make test
make fail-commit
```

`make fail-commit`은 검증 전에 상태를 변경하는 잘못된 구현을 실행합니다. 요청이 실패한 뒤 저장소 내용이 달라지는지 확인하고, prepare-then-반영 구현과 비교합니다.

---

## 1. 실패 분류

| 종류 | 예 | 일반적 처리 위치 |
|---|---|---|
| 외부 입력 오류 | 잘못된 숫자, 누락된 인자 | 파서 또는 요청 경계 |
| 도메인 규칙 위반 | 중복 키, 잔액 부족 | 도메인 객체 또는 서비스 |
| 시스템 오류 | `open`, `read`, `socket` 실패 | 시스템 어댑터와 상위 경계 |
| 자원 부족 | 할당 실패 | 복구 정책이 있는 상위 경계 |
| 프로그래밍 오류 | 불가능한 상태, 잘못된 반복자 | 단언문, 코드 수정 |
| 일시적 상태 | 논블로킹 `EAGAIN` | 재시도 또는 준비 상태 대기 |

분류가 중요한 이유는 호출자가 다르게 행동하기 때문입니다. 잘못된 사용자 입력은 오류 응답을 만들 수 있지만, 내부 불변식 위반을 정상 입력 오류처럼 계속 처리하면 문제를 숨깁니다.

## 2. 반환값과 예외

반환값이 적합한 경우:

- 실패가 흔한 정상 분기입니다.
- 호출자가 즉시 다른 동작을 선택해야 합니다.
- 실패 종류가 작고 명시적입니다.

```cpp
bool Store::contains(const Key &key) const;
```

예외가 적합한 경우:

- 현재 함수가 의미 있는 결과를 만들 수 없습니다.
- 여러 호출 계층을 건너 책임 있는 경계까지 전달해야 합니다.
- 생성자가 유효한 객체를 만들지 못했습니다.
- 실패가 흔한 제어 흐름이 아닙니다.

```cpp
Key::Key(const std::string &text)
{
    if (!isValid(text))
        throw std::invalid_argument("키가 올바르지 않습니다");
}
```

예외와 반환값을 섞어 동일 실패를 두 번 표현하지 않습니다.

## 3. 예외의 실행 흐름

예외가 던져지면 적절한 핸들러를 찾을 때까지 호출 스택을 되감습니다. 그 과정에서 완전히 생성된 자동 객체의 소멸자가 역순으로 호출됩니다.

```cpp
void process()
{
    File input("data.txt");
    Buffer buffer;
    parse(input, buffer); // 여기서 throw
} // File과 Buffer의 소멸자는 스택을 푸는 동안 호출됩니다.
```

정리만 필요하다면 각 단계에서 `catch`하지 않고 RAII에 맡깁니다. 중간 계층이 예외를 잡았다가 같은 정보 없이 다시 던지면 원인과 문맥만 잃습니다.

## 4. 예외를 받는 방법

```cpp
try
{
    run();
}
catch (const DomainError &error)
{
    report(error.what());
}
```

예외는 일반적으로 `const` 참조로 받습니다.

- 불필요한 복사를 피합니다.
- 파생 클래스 exception의 동적 타입을 슬라이싱하지 않습니다.

현재 예외를 그대로 다시 던질 때는 `throw;`를 사용합니다.

```cpp
catch (const std::exception &error)
{
    log(error.what());
    throw;
}
```

`throw error;`는 새 객체를 던져 동적 타입 정보를 잃을 수 있습니다.

## 5. 예외를 잡는 위치

예외는 **처리 책임이 있는 경계**에서 잡습니다.

- 파서 경계: 잘못된 입력을 구조화된 파싱 오류로 바꿈
- 애플리케이션 경계: 도메인 실패를 사용자 응답으로 바꿈
- 프로세스 최상위: 기록 후 안전한 종료 또는 요청 단위 격리

다음 이유만으로 잡지 않습니다.

- “예외가 무섭기 때문에”
- 모든 함수가 로그를 남기게 하기 위해
- 정리 코드를 실행하기 위해

정리는 RAII, 로그는 한 번 의미 있는 문맥이 있는 경계에서 처리합니다.

## 6. 소멸자의 예외 처리

스택을 푸는 동안 다른 예외가 이미 처리되는 상태에서 소멸자가 다시 예외를 내보내면 `std::terminate`로 이어질 수 있습니다. 자원 정리 소멸자는 실패를 내부에서 처리하거나 기록할 수 있는 별도 API를 제공합니다.

```cpp
class Transaction
{
public:
    void commit();   // 실패 보고 가능
    void rollback() throw();
    ~Transaction() throw();
};
```

## 7. 예외 안전성 보장

| 보장 | 실패 뒤 약속 |
|---|---|
| 기본 보장 | 객체는 유효하고 정리 가능하며 누수는 없습니다. 값은 달라질 수 있습니다. |
| 강한 보장 | 성공하거나 호출 전 관측 상태가 그대로입니다. |
| 무예외 보장 | 예외를 밖으로 내보내지 않습니다. |

모든 연산에 강한 예외 안전성이 필요한 것은 아닙니다. 비용과 구현 복잡도를 포함해 실제 호출자가 요구하는 수준을 정합니다.

## 8. prepare-then-반영

기존 상태를 교체하는 연산에 강한 예외 안전성이 필요하면 대상 밖에서 후보를 완성합니다.

```cpp
void Configuration::replace(const Specification &spec)
{
    Configuration candidate;
    candidate.parse(spec);
    candidate.validate();
    swap(candidate); // commit, 예외를 던지지 않아야 함
}
```

다음 질문에 모두 답해야 강한 예외 안전성을 주장할 수 있습니다.

1. 후보 생성 중 얻은 자원은 실패 시 정리됩니까?
2. 후보를 만드는 동안 원본을 전혀 바꾸지 않습니까?
3. 반영 연산은 실패하지 않습니까?
4. 성공 뒤 옛 상태는 누가 정리합니까?
5. alias나 self-assignment가 입력을 무효화하지 않습니까?

## 9. 처리 차이를 표현하는 사용자 예외 타입

예외 클래스를 많이 만드는 것이 좋은 설계는 아닙니다. 호출자가 실제로 다르게 처리할 때만 타입을 나눕니다.

```cpp
class ParseError : public std::runtime_error
{
public:
    explicit ParseError(const std::string &message)
        : std::runtime_error(message)
    {}
};

class ConflictError : public std::runtime_error
{
public:
    explicit ConflictError(const std::string &message)
        : std::runtime_error(message)
    {}
};
```

오류 메시지 문자열을 분석해 분기하기보다 타입이나 구조화된 오류 code를 사용합니다. 반대로 모든 입력 위치마다 다른 예외 클래스를 만들 필요는 없습니다. 행, 열, 원인 같은 데이터는 하나의 파싱 오류에 담을 수 있습니다.

## 10. 입력 파싱 단계 나누기

```text
raw text
→ token 분리
→ 형식 검사
→ 타입 변환
→ 범위 검사
→ 도메인 값 객체
```

`"12abc"`를 숫자 12로 받아들이는지, 전체 입력을 소비해야 하는지 먼저 정합니다. 빈 문자열, 앞뒤 공백, 부호, 앞에 붙은 0과 로캘 정책도 계약입니다.

```cpp
long parseLong(const std::string &text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text.c_str(), &end, 10);

    if (text.empty() || end == text.c_str() || *end != '\0')
        throw ParseError("정수가 아닙니다");
    if (errno == ERANGE)
        throw ParseError("정수 범위를 벗어났습니다");
    return value;
}
```

`errno`는 호출 전에 0으로 만들고 즉시 검사합니다. 다른 함수 호출 뒤까지 오래 보관하지 않습니다.

## 11. 숫자 변환에서 검사할 것

- 입력을 하나도 소비하지 않았습니까?
- 남은 문자가 있습니까?
- 대상 타입 범위를 벗어납니까?
- 부호를 허용합니까?
- 부동소수에서 NaN과 infinity를 허용합니까?
- 정수로 바꿀 때 소수 부분을 어떻게 처리합니까?
- 오버플로와 underflow를 어떻게 보고합니까?

캐스트는 이 검사를 대신하지 않습니다.

## 12. `static_cast`

컴파일 시점에 관계가 알려진 명시적 변환에 사용합니다.

```cpp
double measured = 42.75;
int whole = static_cast<int>(measured);
```

소수 부분이 잘리며, 결과가 대상 정수 타입으로 표현 가능한지 사전에 검사해야 합니다.

안전한 upcast에도 사용할 수 있습니다.

```cpp
Derived *derived = 0;
Base *base = static_cast<Base *>(derived);
```

기반 클래스에서 파생 클래스로 내려가는 캐스트는 문법상 가능할 수 있지만 실제 동적 타입을 검사하지 않습니다. 외부 불변식으로 타입이 확실하지 않다면 `dynamic_cast`를 사용합니다.

## 13. `dynamic_cast`

가상 함수가 있는 polymorphic hierarchy의 실제 타입을 실행 시간에 확인합니다.

```cpp
SpecialHandler *special = dynamic_cast<SpecialHandler *>(handler);
if (special == 0)
{
    // 일치하지 않음
}
```

- 포인터 캐스트 실패: 널
- 참조 캐스트 실패: `std::bad_cast`

불일치가 정상 분기라면 포인터 형태가 자연스럽습니다. 반드시 특정 타입이어야 하는 계약 위반이라면 참조와 예외가 의미 있을 수 있습니다.

빈번한 `dynamic_cast` 연쇄가 나타나면 가상 동작이나 visitor처럼 행동을 객체에 옮길 수 있는지 검토합니다.

## 14. `reinterpret_cast`

낮은 수준의 주소 표현을 바꿉니다. 다음을 제공하지 않습니다.

- 객체 데이터 복사 또는 직렬화
- 포인터가 살아 있는 객체를 가리킨다는 검증
- 수명 연장
- 소유권 이전
- 임의 정수 주소를 역참조해도 된다는 보장

구현이 포인터를 담을 수 있는 `uintptr_t`를 제공할 때만 다음과 같은 토큰을 정의할 수 있습니다.

```cpp
typedef uintptr_t AddressToken;
AddressToken token = reinterpret_cast<AddressToken>(pointer);
Payload *again = reinterpret_cast<Payload *>(token);
```

왕복 표현이 가능해도 원래 객체의 수명이 끝났다면 `again`은 유효하지 않은 포인터입니다. 주소를 파일이나 네트워크에 저장하는 것은 직렬화가 아닙니다.

C++98 환경에는 모든 구현이 제공해야 하는 범용 포인터 정수 타입이 없습니다. `<stdint.h>`가 `uintptr_t`를 제공하는지와 폭이 충분한지 확인합니다.

## 15. `const_cast`

`const_cast`는 cv-qualification만 바꿉니다.

```cpp
const Widget *source = getWidget();
Widget *mutableView = const_cast<Widget *>(source);
```

원래부터 const인 객체를 이 포인터로 수정하면 정의되지 않은 동작이 될 수 있습니다. 잘못된 API의 const 경계를 감추는 용도로 사용하지 않습니다.

## 16. C 스타일 캐스트를 피하는 이유

C 스타일 캐스트 하나는 숫자 변환, 계층 변환, `const` 제거와 주소 재해석을 여러 방식으로 시도할 수 있습니다. 코드 리뷰에서 어떤 위험을 감수했는지 알기 어렵습니다.

C++ 캐스트는 의도를 분리합니다.

```text
값·알려진 타입 관계      → static_cast
실행 시간 계층 확인 → `dynamic_cast`
주소 표현 재해석         → reinterpret_cast
cv 한정만 변경           → const_cast
```

먼저 캐스트 없이 더 정확한 타입이나 함수 시그니처로 표현할 수 있는지 봅니다.

## 17. 오류를 외부 표현으로 바꾸는 경계

내부 예외 문자열을 그대로 사용자에게 보내지 않습니다. 로그와 외부 응답은 목적이 다릅니다.

```cpp
Response Application::execute(const Request &request)
{
    try
    {
        return router_.dispatch(request);
    }
    catch (const ParseError &error)
    {
        log_.write(error.what());
        return Response::badRequest("요청이 올바르지 않습니다");
    }
    catch (const ConflictError &error)
    {
        log_.write(error.what());
        return Response::conflict("현재 상태와 충돌합니다");
    }
}
```

- 내부 로그: 원인, 위치와 디버깅 문맥
- 외부 응답: 안정적인 오류 코드와 노출 가능한 설명

네트워크 서버에서는 한 요청의 오류가 전체 프로세스를 종료하지 않도록 요청 경계를 둡니다. 할당 실패처럼 복구 정책이 없는 오류까지 무조건 정상 응답으로 바꾸지는 않습니다.

---

## 단계형 실습: 안전한 요청 경계

### 1단계: 파서 오류

명령 이름, 인자 수와 숫자 형식을 검사합니다. 오류를 단순 문자열이 아니라 `ParseError`와 위치 정보로 표현합니다.

### 2단계: 도메인 오류

중복 키, 저장 한도 초과와 없는 키 삭제를 서로 다른 결과 또는 예외로 표현합니다.

### 3단계: 최상위 변환

애플리케이션 경계 한곳에서 내부 실패를 `Response`로 바꿉니다. 하위 계층은 출력 문자열을 만들지 않습니다.

### 4단계: 강한 예외 안전성

설정 또는 여러 항목을 한 번에 갱신하는 기능을 후보 객체에 준비한 뒤 `swap`으로 반영합니다.

### 5단계: 스칼라 변환기

다음 입력에 대해 결과를 미리 적고 변환기를 작성합니다.

```text
"0"
"-42"
"42abc"
"2147483648"
"nan"
"+inf"
" 12"
```

### 6단계: 캐스트 실험

- polymorphic 기반 클래스에서 포인터 `dynamic_cast` 성공·실패
- 참조 캐스트 실패와 `std::bad_cast`
- 포인터→정수→포인터 왕복 뒤 원본 객체를 파괴한 경우
- 원래 const 객체를 `const_cast`로 수정하는 코드는 작성만 하고 실행하지 않습니다.

## 예외 분류와 상태 보존 실수

- 정리만 하려고 모든 함수에서 예외를 잡습니다.
- `catch (...)`로 할당 실패와 프로그래밍 오류까지 삼킵니다.
- `throw error;`로 재던져 동적 타입을 잃습니다.
- 기존 상태를 먼저 수정한 뒤 검증합니다.
- `strtol`이 일부 문자만 소비한 입력을 성공으로 취급합니다.
- 캐스트가 범위나 포인터 수명을 검증한다고 가정합니다.
- 내부 파일 경로와 시스템 오류를 사용자 응답에 그대로 노출합니다.

## Rust·Go와 비교하는 오류 처리

Java와 C#의 예외, Rust의 `Result`, Go의 오류 반환값은 문법과 비용 모델이 다릅니다. 그러나 다음 원칙은 유지됩니다.

- 실패 종류를 구분합니다.
- 처리 책임이 있는 경계까지만 전달합니다.
- 실패 뒤 상태를 약속합니다.
- 외부 입력을 타입으로 바꾸기 전에 검증합니다.
- 내부 오류와 사용자 응답을 분리합니다.

## 오류 안전성 점검

- 현재 실패가 정상 분기인지 예외적인 실패인지 설명할 수 있습니까?
- 예외를 잡는 정확한 계층과 그 계층이 할 수 있는 복구를 말할 수 있습니까?
- 강한 예외 안전성의 후보 상태와 반영 지점을 지목할 수 있습니까?
- 문자열 숫자 변환이 입력 전체를 소비했는지 검사합니까?
- 네 가지 C++ 캐스트가 각각 검증하지 않는 것을 말할 수 있습니까?
- 주소 토큰이 남아 있어도 원본 객체를 사용할 수 없는 이유는 무엇입니까?
