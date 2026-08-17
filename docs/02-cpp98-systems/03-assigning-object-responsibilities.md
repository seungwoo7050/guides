# 객체에 책임을 배치하는 방법

## 코드가 커질수록 책임 경계가 필요합니다

클래스를 작성할 수 있다고 프로그램이 자동으로 객체지향적으로 설계되는 것은 아닙니다. 전역 상태를 클래스 안으로 옮기고 모든 필드에 getter와 setter를 붙이면 데이터 위치만 바뀔 뿐 규칙과 판단은 여전히 외부 코드에 흩어집니다.

함께 변하는 상태와 규칙을 찾고, 그 불변식을 지킬 책임을 적절한 객체에 둬야 합니다. 아래 요청 처리 흐름을 기준으로 각 객체가 알아야 할 정보와 변경 이유를 나눕니다.

## 요청 처리 객체의 역할

```text
입력 → RequestParser → Request → CommandService → KeyValueStore
                                      ↓
                                  Response → Formatter → 출력
```

각 화살표를 지나는 값과 오류를 적고, 각 객체에는 서로 밀접하게 관련된 불변식과 동작만 둡니다.

## 명령 서비스를 단계별로 분리

[책임 분리 실습](../../exercises/02-cpp98-systems/object-model/command-service/03-responsibilities/README.md)은 동작은 맞지만 책임이 뒤섞인 시작 코드와, 같은 입출력을 유지하면서 `RequestParser`, `KeyValueStore`, `CommandService`, `ResponseFormatter`로 나눈 참조 구현을 제공합니다.

저장소 루트에서 다음 명령을 실행합니다.

```sh
cd exercises/02-cpp98-systems/object-model/command-service/03-responsibilities
make observe
```

이 단계의 `make observe`는 참조 구현이 아니라 `skeleton/legacy.cpp`에 있는 리팩터링 전 동작을 보여 줍니다. 워크스페이스에서 리팩터링한 뒤 저장소 루트에서 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/03-responsibilities
```

참조 구현은 학습자 구현 검증을 통과한 뒤에만 비교합니다. 참조 구현의 공개 경계를 별도로 검사하려면 저장소 루트에서 다음 명령을 실행합니다.

```sh
make -C exercises/02-cpp98-systems/object-model/command-service/03-responsibilities interface-check
```

`interface-check`는 각 헤더를 외부 코드처럼 포함한 뒤 파싱, 저장, 서비스 실행, 응답 변환을 실제로 연결합니다. 파일 이름이나 특정 문자열만 찾는 검사와 달리 공개 타입들이 함께 컴파일되고 같은 동작을 만드는지 확인합니다. 저장 용량 검사를 `main`으로 옮겨 본 뒤에도 이 검사가 잡지 못하는 설계 문제가 무엇인지 기록합니다.

---

## 1. 절차적 코드에서 시작하기

처음부터 완벽한 객체 구조를 설계하려 하지 않습니다. 먼저 작동하는 작은 흐름을 만든 뒤 변경과 오류가 반복해서 모이는 지점을 관찰합니다.

```cpp
void execute(
    const std::vector<std::string> &tokens,
    std::map<std::string, std::string> &values,
    std::ostream &out)
{
    if (tokens.empty())
        return;

    if (tokens[0] == "PUT")
    {
        if (tokens.size() != 3)
            out << "ERR arguments\n";
        else
            values[tokens[1]] = tokens[2];
    }
    else if (tokens[0] == "GET")
    {
        // 조회, 오류 처리, 출력이 한곳에 섞임
    }
}
```

작은 프로그램에서는 이 구조로 충분할 수 있습니다. 기능이 늘어나면 서로 다른 변경 이유가 한 함수에 쌓이는 것이 문제입니다.

- 입력 문법 변경
- 키 검증 규칙 변경
- 저장 정책 변경
- 응답 형식 변경
- 새 명령 추가

리팩터링은 클래스를 많이 만드는 작업이 아니라 서로 다른 변경 이유를 적절한 경계로 나누는 작업입니다.

## 2. 불변식부터 찾기

불변식은 공개 연산 전후에 항상 성립해야 하는 조건입니다.

예를 들어 키-값 저장소의 규칙이 다음과 같다고 가정합니다.

```text
- key는 비어 있지 않습니다.
- key는 영문자, 숫자, '_'만 포함합니다.
- 저장 가능한 항목 수에는 상한이 있습니다.
- 하나의 key에는 현재 값이 최대 하나만 존재합니다.
```

모든 호출자가 이 규칙을 반복해서 검사하면 누락되기 쉽습니다. 키 생성과 저장소 변경 경로에 검사를 모읍니다.

```cpp
class Key
{
public:
    explicit Key(const std::string &text);
    const std::string &text() const;

private:
    std::string text_;
};
```

`Key` 생성에 성공했다면 형식이 유효하다고 가정할 수 있어야 합니다. 이후 객체는 같은 검사를 반복하지 않습니다.

## 3. 클래스를 추출하는 기준

요구사항 문장에 나온 명사를 모두 클래스로 만들지 않습니다. 다음 질문 중 여러 항목에 해당한다면 독립된 타입 후보로 검토합니다.

- 자체 불변식이 있는가
- 상태와 동작이 함께 변하는가
- 독립된 수명을 가지는가
- 다른 코드와 다른 이유로 변경되는가
- 별도로 테스트할 가치가 있는가
- 의미 있는 타입으로 만들면 잘못된 조합을 막을 수 있는가

`Color`, `Manager`, `Data`처럼 이름만으로 역할과 책임이 드러나지 않는 타입은 다시 검토합니다.

## 4. 상태와 행동을 함께 둡니다

다음 설계는 필드를 숨겼지만 핵심 규칙은 외부 코드에 남아 있습니다.

```cpp
if (account.balance() >= amount)
    account.setBalance(account.balance() - amount);
```

동시 호출이 생기거나 수수료와 한도 규칙이 추가되면 모든 호출 지점을 수정해야 합니다. 상태를 꺼내 직접 계산하기보다 객체에 의미 있는 행동을 요청합니다.

```cpp
if (!account.withdraw(amount))
    return insufficientFunds();
```

이 구조의 장점은 코드가 짧아지는 데 그치지 않습니다.

- 잔액 변경 경로가 한곳에 모입니다.
- 음수 금액, 수수료, 한도를 일관되게 검사할 수 있습니다.
- 호출자는 내부 표현을 알 필요가 없습니다.

이 원칙을 흔히 **Tell, Don’t Ask**라고 부릅니다. 절대 규칙은 아닙니다. 조회가 핵심인 읽기 모델과 화면 출력에는 관찰 함수가 필요합니다. 중요한 점은 상태를 읽은 뒤 외부 코드가 객체의 핵심 불변식을 다시 구현하지 않는 것입니다.

## 5. getter와 setter를 추가하기 전에

```cpp
class Session
{
public:
    void setRegistered(bool value);
    void setNick(const std::string &nick);
    void setUser(const std::string &user);
};
```

이 인터페이스는 다음과 같은 잘못된 상태를 허용할 수 있습니다.

- nick이나 user가 없는데 `registered`가 `true`
- 등록 완료 후 nick과 user가 모순되게 변경됨
- 등록 완료 이벤트가 여러 번 발생함

상태 전이를 의미 있는 함수로 제한합니다.

```cpp
class Session
{
public:
    void setNick(const Nick &nick);
    void setUser(const UserInfo &user);
    bool completeRegistration();
    bool isRegistered() const;
};
```

`completeRegistration`은 필요한 정보가 모두 있는지 확인하고 허용된 상태에서 한 번만 전이시킵니다.

## 6. 객체 사이의 협력

하나의 객체가 모든 일을 처리할 필요는 없습니다. 각 객체가 작은 책임을 맡고 값과 결과를 주고받습니다.

```text
입력 문자열
→ RequestParser
→ Request
→ CommandService
→ KeyValueStore
→ Response
→ ResponseFormatter
```

각 경계의 질문은 다음과 같습니다.

- `RequestParser`: 문자열 문법이 유효한가
- `Request`: 어떤 명령과 인자가 들어 있는가
- `CommandService`: 요청을 어떤 도메인 동작으로 연결하는가
- `KeyValueStore`: 저장 규칙과 현재 상태를 유지하는가
- `ResponseFormatter`: 결과를 어떤 외부 문자열로 표현하는가

파서가 저장소를 직접 변경하거나 저장소가 스트림에 출력하면 서로 다른 변경 이유가 다시 섞입니다.

## 7. 합성을 기본으로 사용합니다

합성은 한 객체가 다른 객체를 멤버 또는 참조로 사용해 기능을 구성하는 방식입니다.

```cpp
class Application
{
public:
    Application(KeyValueStore &store, std::ostream &out)
        : store_(store), out_(out)
    {}

    void run();

private:
    KeyValueStore &store_; // 소유하지 않고 빌림
    std::ostream &out_;    // 소유하지 않고 빌림
};
```

합성은 다음 관계를 드러냅니다.

- 포함된 객체의 수명
- 외부에서 전달된 의존성
- 어떤 기능을 다른 객체에 위임하는가
- 구현을 교체할 수 있는 경계가 어디인가

코드 몇 줄을 재사용하려는 이유만으로 상속하지 않습니다. 상속은 다음 문서에서 대체 가능성을 요구하는 관계로 다룹니다.

## 8. 상태 전이를 명시합니다

여러 불리언으로 상태를 나타내면 불가능하거나 모순된 조합이 생기기 쉽습니다.

```cpp
bool connected;
bool registered;
bool closing;
```

세 값은 8개 조합을 만들지만 실제로 허용할 상태는 훨씬 적을 수 있습니다.

```cpp
class ConnectionState
{
public:
    enum Value
    {
        ACCEPTED,
        REGISTERING,
        ACTIVE,
        CLOSING,
        CLOSED
    };
};
```

상태 기계를 설계할 때는 전이를 표로 정리합니다.

| 현재 상태 | 이벤트 | 다음 상태 | 거부 조건 |
|---|---|---|---|
| ACCEPTED | 첫 정보 수신 | REGISTERING | 형식 오류 |
| REGISTERING | 필수 정보 완료 | ACTIVE | 중복 또는 누락 |
| ACTIVE | 종료 요청 | CLOSING | 없음 |
| CLOSING | 출력 완료 | CLOSED | 없음 |

객체는 허용된 전이만 공개 함수로 제공합니다. 상태 값 자체를 임의로 지정하는 setter는 노출하지 않습니다.

## 9. 응집도와 변경 이유

응집도가 높은 클래스는 서로 관련된 상태와 동작을 함께 가집니다. 하나의 클래스가 다음 이유로 모두 변경된다면 책임이 지나치게 많을 가능성이 큽니다.

- 입력 문법 변경
- 저장 방식 변경
- 화면 출력 변경
- 네트워크 전송 변경
- 접근 권한 변경

클래스의 줄 수보다 **서로 다른 변경 이유의 개수**가 더 중요합니다. 반대로 한 줄짜리 함수마다 클래스를 만들면 전체 흐름을 추적하기 어렵습니다. 독립된 규칙, 수명, 변경 이유, 교체 가능성이 있을 때 경계를 분리합니다.

## 10. 계층 간 의존성을 좁힙니다

도메인 객체가 스트림, 소켓 파일 디스크립터, 파일 경로 같은 외부 표현을 직접 알면 테스트와 재사용이 어려워집니다.

```text
외부 표현 계층: 문자열, 파일, 소켓
애플리케이션 계층: 요청을 사용 사례에 연결
도메인 계층: 상태와 규칙
```

예를 들어 `KeyValueStore::put`은 `std::cout`에 직접 오류를 출력하지 않습니다. 성공 여부나 도메인 결과를 반환하고 외부 경계가 이를 텍스트, HTTP 상태 등으로 변환합니다.

## 11. 객체 역할을 설명하는 용어

용어를 먼저 암기하기보다 리팩터링한 객체의 역할을 설명할 때 사용합니다.

### 값 객체

속성으로 식별되며 같은 값은 동등한 의미를 가집니다. 유효한 값만 생성하고 복사 후 원본과 독립적입니다.

- `Key`
- `UserId`
- `Path`
- `Money`

### 식별자를 가진 객체

현재 속성이 같아도 서로 다른 수명을 가진 별도 객체입니다. 시간에 따라 상태가 변합니다.

- 연결
- 세션
- 주문

### 서비스

하나의 값 객체에 자연스럽게 속하지 않는 사용 사례를 조율합니다.

- 요청을 저장소 동작에 연결
- 여러 객체가 참여하는 작업 수행

모든 로직을 `SomethingService`에 넣으면 도메인 객체는 데이터만 담는 구조가 됩니다. 서비스는 흐름을 조율하고, 개별 객체의 불변식은 해당 객체가 지킵니다.

## 12. 다른 객체지향 언어에도 적용되는 원칙

| 원칙 | C++ 표현 | 다른 언어에서 흔한 표현 |
|---|---|---|
| 유효한 값만 생성 | 생성자 검증 | 생성자·팩터리·레코드 검증 |
| 읽기 전용 경계 | `const T&`, `const` 멤버 함수 | 불변 객체·읽기 전용 속성 |
| 협력 구성 | 멤버와 참조 | 생성자 주입·합성 |
| 상태 전이 제한 | 비공개 상태 + 의미 있는 함수 | 메서드·리듀서·상태 객체 |
| 값 객체 | 값 의미론을 가진 클래스 | 레코드·데이터 클래스·구조체 |

문법이 달라도 누가 규칙을 알고 누가 상태를 바꾸는지는 항상 결정해야 합니다.

---

## 단계형 실습: 요청 처리기 리팩터링

### 시작 코드

하나의 함수가 입력 파싱, 저장소 변경, 출력을 모두 수행하는 절차적 프로그램에서 시작합니다.

### 1단계: 값 객체 추출

- `Key`
- `Value`
- `Request`
- `Response`

잘못된 키는 `Key` 객체로 생성되지 않게 합니다.

### 2단계: 책임 분리

- `RequestParser`
- `KeyValueStore`
- `CommandService`
- `ResponseFormatter`

각 타입의 책임과 변경 이유를 한 문장으로 기록합니다.

### 3단계: 상태 규칙 이동

저장소 최대 크기, 중복 키 정책, 삭제 규칙을 `KeyValueStore` 안으로 옮깁니다.

### 4단계: 출력 교체

텍스트 formatter를 JSON과 비슷한 formatter로 교체합니다. 저장소와 서비스는 수정하지 않습니다.

### 5단계: 변경으로 경계 검증

다음 요구사항을 하나씩 적용하고 수정한 파일을 기록합니다.

- 키 길이 상한 추가
- `PUT` 덮어쓰기 금지
- 저장소 전체 읽기 전용 모드
- 출력 형식 변경
- 새 명령 `EXISTS`

하나의 요구사항 때문에 관계없는 여러 계층이 함께 바뀐다면 책임 경계를 다시 검토합니다.

## 책임 분리 과정에서 자주 생기는 문제

- 요구사항에 나온 모든 명사를 클래스로 만듭니다.
- getter와 setter로 비공개 필드를 사실상 그대로 노출합니다.
- 파서가 저장소 변경과 출력까지 담당합니다.
- 모든 동작을 하나의 서비스에 모읍니다.
- 포함 관계를 불필요한 상속으로 표현합니다.
- 상태를 여러 불리언으로 흩어 모순된 조합을 허용합니다.
- 디자인 패턴 이름은 사용하지만 어떤 문제를 해결했는지 설명하지 못합니다.

## 객체별 책임 배치 점검

- 각 클래스가 지키는 불변식을 한 문장으로 설명할 수 있습니까?
- 특정 상태 변경이 어느 공개 함수만 통과하는지 지목할 수 있습니까?
- 상태를 꺼내 변경하지 않고 객체에 의미 있는 행동을 요청할 수 있습니까?
- 합성 관계의 소유 객체와 빌린 의존성을 구분할 수 있습니까?
- 새 요구사항이 어느 객체만 변경해야 하는지 예측할 수 있습니까?
- 객체 버전이 절차적 버전의 어떤 실제 문제를 해결했는지 설명할 수 있습니까?
