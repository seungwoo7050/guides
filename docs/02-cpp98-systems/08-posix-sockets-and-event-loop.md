# POSIX 소켓과 이벤트 루프

## 연결마다 달라지는 상태를 관리합니다

논블로킹 서버는 파일 디스크립터 수명, 부분 읽기·쓰기, `EINTR`, `EAGAIN`, 준비 상태 등록과 연결 삭제 순서를 동시에 지켜야 합니다. 하나라도 틀리면 간헐적 데이터 손실, 바쁜 반복, 파일 디스크립터 누수 또는 해제 후 사용이 생깁니다. 리스너와 연결의 소유자를 먼저 정한 뒤 POSIX/BSD 소켓을 C++ 객체 수명과 이벤트 루프로 연결합니다.

## 준비 상태 통지에서 입출력까지

```text
커널 준비 상태 통지 → 이벤트 루프 → fd로 Connection 조회
                                         ├→ recv → 입력 버퍼
                                         └→ 출력 버퍼 → send

소유자 삭제 → 폴러 등록 해제 → fd 닫기
```

준비 상태는 작업 완료가 아니라 “지금 시도하면 진행될 가능성이 있다”는 통지입니다.

## line-server로 이벤트 루프 확인

`../exercises/02-cpp98-systems/networking/line-server`는 블로킹 단일 연결 서버에서 시작해, 플랫폼별 poller를 사용하는 논블로킹 참조 서버까지 제공합니다.

```sh
cd ../exercises/02-cpp98-systems/networking/line-server
make observe
make test
make stress
make leak-check
```

테스트는 실제 TCP 연결을 열어 부분 프레임, 여러 프레임의 병합, 동시 클라이언트, 느린 수신자, `QUIT` 후 EOF와 SIGTERM 종료를 검증합니다. Linux에서는 epoll, macOS/BSD에서는 kqueue 구현이 선택됩니다.

---

## 1. 자원으로 관리하는 파일 디스크립터

프로그램에서는 파일 디스크립터가 작은 정수로 보이지만 실제 소켓 상태와 버퍼는 커널이 소유합니다. 파일 디스크립터를 닫지 않으면 커널 자원이 누수됩니다. 닫힌 파일 디스크립터 번호는 곧 다른 자원에 재사용될 수 있으므로 옛 번호를 보관한 코드가 전혀 다른 소켓을 건드릴 수도 있습니다.

각 파일 디스크립터에 대해 다음을 답합니다.

- 소유자는 누구입니까?
- 어느 시점부터 소유자가 됩니까?
- 누가 `close`합니까?
- 소유자가 이동하거나 컨테이너에서 제거될 때 어떤 순서로 정리됩니까?
- 이벤트 백엔드 등록은 파일 디스크립터 수명보다 길게 남지 않습니까?

## 2. 수신 대기 소켓 생성 순서

```text
socket
→ fd flag 설정
→ socket option 설정
→ bind
→ listen
→ event backend 등록
```

```cpp
int makeListener(const char *addressText, unsigned short port)
{
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
        throw SystemError("socket", errno);

    try
    {
        setCloseOnExec(fd);
        setNonBlocking(fd);

        int enabled = 1;
        if (::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR,
                         &enabled, sizeof(enabled)) == -1)
            throw SystemError("setsockopt", errno);

        // address 구성, bind, listen
        return fd;
    }
    catch (...)
    {
        ::close(fd);
        throw;
    }
}
```

원시 파일 디스크립터가 RAII 객체에 들어가기 전 짧은 구간은 수동 정리가 필요합니다. 더 엄격하게는 `socket` 반환 즉시 `UniqueFd`로 감쌉니다.

## 3. 주소 구조체와 바이트 order

IPv4 주소는 `sockaddr_in`에 저장합니다.

```cpp
sockaddr_in address;
std::memset(&address, 0, sizeof(address));
address.sin_family = AF_INET;
address.sin_port = htons(port);

if (::inet_pton(AF_INET, addressText, &address.sin_addr) != 1)
    throw std::invalid_argument("IPv4 주소가 올바르지 않습니다");
```

- 포트는 네트워크 바이트 순서로 바꿉니다.
- `inet_pton`은 성공 1, 형식 오류 0, 다른 오류 -1을 구분합니다.
- 범용 소켓 함수에는 `sockaddr*`로 전달합니다.
- 상대 주소를 받을 때는 충분히 큰 `sockaddr_storage`를 사용할 수 있습니다.

```cpp
if (::bind(fd, reinterpret_cast<sockaddr *>(&address),
           sizeof(address)) == -1)
    throw SystemError("bind", errno);
```

## 4. 연결 수락과 소유권 이전

listen 파일 디스크립터는 연결을 받는 소켓이고 `accept`는 각 클라이언트용 새 파일 디스크립터를 반환합니다.

```cpp
while (true)
{
    sockaddr_storage peer;
    socklen_t length = sizeof(peer);
    int client = ::accept(listener,
        reinterpret_cast<sockaddr *>(&peer), &length);

    if (client >= 0)
    {
        // 클라이언트를 설정하고 소유자에게 인계합니다.
        continue;
    }

    if (errno == EINTR)
        continue;
    if (errno == EAGAIN || errno == EWOULDBLOCK)
        break;

    reportSystemError("accept", errno);
    break;
}
```

준비 상태 한 번에 대기 중인 연결이 여러 개일 수 있으므로 `EAGAIN`이 날 때까지 수락합니다. 클라이언트 설정이나 컨테이너 삽입이 실패하면 그 파일 디스크립터를 닫아야 합니다.

## 5. 논블로킹과 실행 시 닫기

기존 플래그를 읽고 필요한 비트만 추가합니다.

```cpp
void setNonBlocking(int fd)
{
    int flags = ::fcntl(fd, F_GETFL, 0);
    if (flags == -1)
        throw SystemError("fcntl F_GETFL", errno);
    if (::fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
        throw SystemError("fcntl F_SETFL", errno);
}
```

```cpp
void setCloseOnExec(int fd)
{
    int flags = ::fcntl(fd, F_GETFD, 0);
    if (flags == -1)
        throw SystemError("fcntl F_GETFD", errno);
    if (::fcntl(fd, F_SETFD, flags | FD_CLOEXEC) == -1)
        throw SystemError("fcntl F_SETFD", errno);
}
```

`F_SETFL, O_NONBLOCK`만 호출하면 기존 상태 플래그를 잃을 수 있습니다. Linux의 `accept4`는 연결 수락과 플래그 설정을 합칠 수 있지만 다른 플랫폼을 지원한다면 `accept` + `fcntl` 경로가 필요합니다.

## 6. 시스템 호출 결과 분류

논블로킹 I/O의 `-1`은 항상 치명적 오류가 아닙니다.

| 결과 | 의미 | 일반 처리 |
|---|---|---|
| `> 0` | 처리한 바이트 수 | 오프셋과 버퍼 갱신 |
| `recv`에서 `== 0` | 상대가 정상적으로 쓰기 방향 종료 | EOF 상태 기록 |
| `-1`, `EINTR` | 시그널로 중단 | 다시 시도 |
| `-1`, `EAGAIN/EWOULDBLOCK` | 지금은 처리 불가 | 준비 상태 대기로 돌아감 |
| 그 외 `-1` | 실제 오류 | 연결 종료 요청과 기록 |

`errno`는 실패 직후 읽습니다. 로그 조립처럼 다른 함수 호출을 한 뒤에는 값이 바뀔 수 있습니다.

## 7. 부분 읽기와 입력 버퍼

TCP는 메시지 경계를 보존하지 않습니다. 한 `recv`는 다음 중 어느 형태든 반환할 수 있습니다.

```text
명령 절반
명령 하나
여러 명령
마지막 명령의 일부
```

연결마다 입력 버퍼를 둡니다.

```cpp
ReadResult Connection::readAvailable()
{
    char buffer[4096];
    ReadResult result;

    while (true)
    {
        ssize_t count = ::recv(fd_, buffer, sizeof(buffer), 0);

        if (count > 0)
        {
            input_.append(buffer, static_cast<std::size_t>(count));
            if (input_.size() > maxInputBytes_)
                return ReadResult::limitExceeded();
            continue;
        }
        if (count == 0)
            return ReadResult::peerClosed();
        if (errno == EINTR)
            continue;
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return result;
        return ReadResult::error(errno);
    }
}
```

프로토콜 프레이밍은 별도 계층이 `input_`에서 완성된 프레임만 꺼냅니다. 소켓 계층이 명령 문법이나 HTTP를 알지 않게 합니다.

## 8. 부분 쓰기와 출력 버퍼

`send`가 요청한 바이트 전부를 보낸다는 보장은 없습니다.

```cpp
WriteResult Connection::flush()
{
    while (writeOffset_ < output_.size())
    {
        const char *data = output_.data() + writeOffset_;
        std::size_t left = output_.size() - writeOffset_;
        ssize_t count = ::send(fd_, data, left, sendFlags());

        if (count > 0)
        {
            writeOffset_ += static_cast<std::size_t>(count);
            continue;
        }
        if (count == -1 && errno == EINTR)
            continue;
        if (count == -1 &&
            (errno == EAGAIN || errno == EWOULDBLOCK))
            return WriteResult::wouldBlock();
        return WriteResult::error(errno);
    }

    output_.clear();
    writeOffset_ = 0;
    return WriteResult::complete();
}
```

보낸 만큼 오프셋을 전진시킵니다. 앞부분을 매번 `erase`하면 큰 버퍼에서 반복 이동 비용이 생길 수 있으므로 오프셋을 사용하고 일정 크기 이상 진행됐을 때만 압축합니다.

## 9. 역압

상대가 읽지 않으면 커널 송신 버퍼가 차고 애플리케이션 출력 버퍼가 계속 커질 수 있습니다. 이를 방치하면 느린 클라이언트 몇 개가 전체 프로세스 메모리를 소모합니다.

연결별 정책을 둡니다.

```text
pending output <= maxPendingBytes
```

상한을 넘으면 선택할 수 있는 정책:

- 오류 응답을 넣을 공간이 있다면 응답 후 종료
- 즉시 연결 종료
- 읽기 감시 대상를 잠시 끄고 출력을 먼저 비움

정책은 프로토콜과 서비스 요구에 맞게 정하되 버퍼가 무한히 자라지 않게 합니다.

## 10. 준비 상태 통지의 의미

읽기 준비 상태는 “블로킹 없이 읽을 가능성이 있다”는 뜻이지 한 메시지가 완성됐다는 뜻이 아닙니다. 쓰기 준비 상태도 전체 출력을 다 보낼 수 있다는 보장이 아닙니다.

준비 상태 이벤트 뒤에도 실제 시스템콜 결과를 `EINTR`, `EAGAIN`, EOF와 오류로 다시 분류합니다.

## 11. `select`, `poll`, `epoll`, `kqueue`

| API | 범위 | 모델 |
|---|---|---|
| `select` | POSIX | 파일 디스크립터 set을 매번 전달, 파일 디스크립터 수 제한 가능 |
| `poll` | POSIX | pollfd 배열을 매번 전달 |
| `epoll` | Linux | 관심 파일 디스크립터를 커널에 등록, 준비 이벤트만 반환 |
| `kqueue` | BSD/macOS | 파일 디스크립터의 읽기/쓰기 필터 등을 별도 등록 |

표면 API는 다르지만 애플리케이션이 필요한 공통 책임은 작습니다.

```text
add(fd, interests)
update(fd, interests)
remove(fd)
wait(timeout)
```

애플리케이션과 연결 객체가 운영체제 이벤트 플래그를 직접 다루지 않게 합니다.

## 12. 레벨 트리거와 에지 트리거

### 레벨 트리거

준비 상태가 계속되면 다음 wait에서도 다시 통지됩니다. 한 번에 모두 처리하지 못해도 다음 기회가 있어 구현이 단순합니다.

### 에지 트리거

not-준비에서 준비로 바뀐 순간을 중심으로 통지합니다. 이벤트를 받으면 `EAGAIN`까지 drain하지 않을 경우 남은 데이터가 있어도 새 통지가 오지 않을 수 있습니다.

첫 구현은 레벨-triggered로 만듭니다. LT에서도 한 이벤트에 가능한 만큼 처리하면 syscall과 이벤트 수를 줄일 수 있습니다.

## 13. 이벤트 루프의 불변식

이벤트 루프는 다음 불변식을 유지해야 합니다.

```text
등록된 client fd에는 정확히 하나의 Connection owner가 있습니다.
닫힌 fd는 backend와 connection table에 남지 않습니다.
Connection을 삭제하는 동안 callback이 옛 주소를 사용하지 않습니다.
보낼 데이터가 없으면 WRITE interest가 없습니다.
한 iteration에서 같은 fd를 두 번 close하지 않습니다.
```

기본 루프:

```cpp
while (!stopRequested_)
{
    std::vector<Event> events = poller_.wait(timeoutMs);

    for (std::size_t i = 0; i < events.size(); ++i)
    {
        const Event &event = events[i];
        if (event.fd == listener_.get())
            acceptReadyClients();
        else
            handleClientEvent(event);
    }

    applyDeferredCloses();
    processTimers();
}
```

반복 중 컨테이너를 바로 지우면 이후 이벤트나 콜백이 삭제된 객체를 참조할 수 있습니다. 종료 요청을 표시하고 안전한 지점에 모아서 처리하는 방법이 단순합니다.

## 14. 연결 객체의 책임

`Connection`은 소켓 파일 디스크립터와 연결별 바이트 상태를 소유합니다.

```text
fd
input buffer
output buffer와 write offset
max input/output limit
peer closed 여부
close requested 여부
마지막 활동 시각
```

다음은 분리합니다.

- 프로토콜 파서와 command 처리
- 전체 연결 table
- 이벤트 백엔드
- 서버 전체 설정

연결이 “읽고 쓸 바이트”를 관리하고 파서가 “바이트가 어떤 메시지인지”를 관리하면 프로토콜을 바꿔도 이벤트 루프가 흔들리지 않습니다.

## 15. 필요한 동안만 쓰기 준비 상태 감시

TCP 소켓은 대개 쓰기 준비 상태입니다. 보낼 데이터가 없는데 쓰기를 계속 등록하면 대기 함수가 즉시 반환하는 바쁜 반복이 됩니다.

```cpp
Interest desired = Interest::READ;
if (connection.hasPendingOutput())
    desired |= Interest::WRITE;

poller_.update(connection.fd(), desired);
```

- 출력 큐가 비어 있다가 데이터가 생김 → 쓰기 추가
- flush가 모두 완료됨 → 쓰기 제거
- 쓰기 뒤 닫기 상태 → 읽기를 끄고 쓰기만 유지할 수 있음

감시 대상 계산을 한 함수에 모아 상태 변경 뒤 항상 호출합니다.

## 16. `SIGPIPE`와 `EINTR`

닫힌 소켓에 `send`하면 프로세스에 `SIGPIPE`가 전달될 수 있으며 기본 동작은 종료입니다.

대응 방법:

- 프로세스에서 `SIGPIPE` 무시
- Linux의 `MSG_NOSIGNAL`
- BSD/macOS의 `SO_NOSIGPIPE`

플랫폼별 지원을 감싼 `sendFlags` 또는 소켓 설정 helper를 둡니다.

`EINTR`은 시그널 때문에 시스템콜이 중단됐다는 뜻입니다. 일반 I/O에서는 재시도할 수 있지만, 프로세스 종료 시그널로 이벤트 wait를 깨우려는 설계에서는 stop 플래그를 먼저 확인합니다.

## 17. C++98 `UniqueFd`

```cpp
class UniqueFd
{
public:
    UniqueFd() : fd_(-1) {}
    explicit UniqueFd(int fd) : fd_(fd) {}

    ~UniqueFd()
    {
        reset();
    }

    int get() const { return fd_; }
    bool valid() const { return fd_ != -1; }

    int release()
    {
        int result = fd_;
        fd_ = -1;
        return result;
    }

    void reset(int fd = -1)
    {
        if (fd_ != -1)
            ::close(fd_);
        fd_ = fd;
    }

    void swap(UniqueFd &other)
    {
        int temporary = fd_;
        fd_ = other.fd_;
        other.fd_ = temporary;
    }

private:
    UniqueFd(const UniqueFd &);
    UniqueFd &operator=(const UniqueFd &);

    int fd_;
};
```

C++98에는 이동 의미론이 없으므로 소유권 전달을 `release`, `reset`, `swap` 같은 명시적 동작으로 제한합니다. 함수가 원시 파일 디스크립터를 반환하면 인계 지점을 즉시 소유자에 넣습니다.

## 18. 공통 Poller 인터페이스

```cpp
struct Event
{
    int fd;
    bool readable;
    bool writable;
    bool hangup;
    int errorCode;
};

class Poller
{
public:
    virtual ~Poller() {}
    virtual void add(int fd, unsigned int interests) = 0;
    virtual void update(int fd, unsigned int interests) = 0;
    virtual void remove(int fd) = 0;
    virtual std::vector<Event> wait(int timeoutMs) = 0;
};
```

Linux 백엔드는 파일 디스크립터 하나의 비트 마스크를 `epoll_ctl`로 갱신합니다. `kqueue` 백엔드는 읽기와 쓰기 필터를 별도로 추가·삭제합니다. 이 차이는 백엔드 안에 머물러야 합니다.

## 19. 연결 삭제와 콜백 수명

위험한 흐름:

```text
Connection callback 호출
→ callback이 server.disconnect(fd)
→ map에서 Connection 삭제
→ 원래 함수가 Connection을 계속 사용
```

방어 방법:

- 콜백 중에는 `closeRequested`만 표시
- 현재 반복 끝에서 지연 삭제
- 삭제 전 필요한 데이터를 값으로 복사
- map에서 소유자를 local 변수로 옮긴 뒤 콜백 완료 후 파괴

원시 포인터를 빌려 쓸 때 소유자 삭제 가능성이 있는 호출을 사이에 두지 않습니다.

## 20. 이벤트 루프에 타이머 추가하기

유휴 제한 시간과 작업 제한 시간을 위해 연결별 마지막 활동 시각을 기록합니다. 첫 구현에서는 대기 제한 시간 뒤 전체 연결을 순회해도 규모가 작다면 충분합니다.

확장 후보:

- 최소 힙 타이머 큐
- Linux `timerfd`
- kqueue `EVFILT_TIMER`

자료구조를 선택할 때 정확성부터 확보하고 실제 연결 수와 타이머 변경 빈도를 측정합니다.

---

## 단계형 실습: 논블로킹 줄 서버

### 1단계: 블로킹 단일 연결

`socket → bind → listen → accept` 순서로 한 클라이언트의 줄을 echo합니다. 이 단계에서는 이벤트 루프를 만들지 않습니다.

검증:

- 재시작 시 bind 가능
- 클라이언트 EOF 처리
- 오류 경로 파일 디스크립터 정리

### 2단계: `UniqueFd`

리스너와 클라이언트 파일 디스크립터를 RAII 소유자에 넣습니다. 일부러 중간 예외를 만들고 파일 디스크립터가 닫혔는지 확인합니다.

### 3단계: 논블로킹과 Poller 한 백엔드

현재 OS의 `epoll` 또는 `kqueue` 하나만 구현합니다. 리스너 준비 상태와 여러 클라이언트를 처리합니다.

### 4단계: 연결 버퍼

한 번에 여러 줄, 여러 번에 나뉜 한 줄을 모두 처리합니다.

```text
send #1: "PUT a"
send #2: " 1\nGET a\n"
```

### 5단계: 부분 쓰기와 역압

연결별 출력 버퍼, 오프셋과 쓰기 감시 대상 토글을 추가합니다. 느린 클라이언트를 흉내 내 출력 상한이 작동하는지 봅니다.

### 6단계: 안전한 종료

콜백에서는 닫기 요청만 표시하고 반복 끝에서 삭제합니다. 상대 EOF, 프로토콜 오류, 송신 오류와 서버 중지 경로를 각각 테스트합니다.

### 7단계: 두 번째 백엔드

공통 `Poller` 계약을 유지한 채 다른 플랫폼 백엔드를 추가합니다. 애플리케이션 코드에 운영체제 상수가 드러나지 않는지 확인합니다.

## 테스트 항목

- 리스너 생성 단계별 실패
- 수락 뒤 설정 실패
- `socketpair`를 이용한 부분 읽기/쓰기
- 한 `send`에 여러 프레임
- 한 프레임을 여러 `send`로 분할
- 상대 EOF
- 출력 버퍼 상한
- 콜백 중 닫기 요청
- 여러 클라이언트의 상태 독립성
- 반복 연결·종료 뒤 파일 디스크립터 수 증가 여부
- stop 시그널 뒤 이벤트 wait 종료

## 논블로킹 소켓에서 생기는 오류

- 수락한 파일 디스크립터를 설정 실패 경로에서 닫지 않습니다.
- `recv == 0`을 `EAGAIN`처럼 처리합니다.
- 한 `recv`가 한 메시지라고 가정합니다.
- `send` 반환값과 요청 길이가 같다고 가정합니다.
- 출력이 없는데 쓰기를 계속 등록합니다.
- 간선-triggered에서 `EAGAIN`까지 drain하지 않습니다.
- 파일 디스크립터를 닫기 전에 백엔드 등록을 정리하지 않습니다.
- 콜백이 연결을 삭제한 뒤 원래 함수가 계속 접근합니다.
- SIGPIPE 대응 없이 닫힌 상대에 씁니다.
- 원시 파일 디스크립터 소유자가 여러 객체에 흩어집니다.

## Rust·Go와 비교하는 이벤트 처리

노드.js, Java NIO, Netty, Rust Tokio와 Python asyncio는 API는 다르지만 같은 상태를 관리합니다.

```text
연결별 input/output state
readiness 또는 completion event
부분 I/O
backpressure
제한 시간
연결 수명
```

프레임워크가 이벤트 루프를 감추더라도 핸들러가 느린 클라이언트, 취소와 연결 종료를 어떻게 처리하는지는 여전히 중요합니다.

## 소켓·이벤트 루프 점검

- 리스너 파일 디스크립터와 클라이언트 파일 디스크립터의 소유자를 각각 지목할 수 있습니까?
- `recv`의 다섯 결과 경로를 설명할 수 있습니까?
- 읽기 준비 상태가 완성된 메시지를 뜻하지 않는 이유는 무엇입니까?
- 쓰기 감시 대상을 항상 등록하면 어떤 반복이 생깁니까?
- 출력 버퍼 상한이 필요한 이유와 초과 정책은 무엇입니까?
- 이벤트 반복 중 연결 삭제를 지연하는 이유는 무엇입니까?
- `epoll`과 `kqueue` 차이가 애플리케이션에 새지 않습니까?
