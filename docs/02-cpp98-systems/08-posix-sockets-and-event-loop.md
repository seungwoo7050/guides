# POSIX 소켓과 이벤트 루프

## 연결마다 달라지는 상태를 관리합니다

논블로킹 서버는 파일 디스크립터 수명, 부분 읽기·쓰기, `EINTR`, `EAGAIN`, 준비 상태 등록과 연결 삭제 순서를 함께 관리해야 합니다. 하나라도 잘못 처리하면 간헐적인 데이터 손실, 바쁜 대기, 파일 디스크립터 누수나 해제 후 사용이 발생합니다. 먼저 리스너와 각 연결의 소유자를 정한 뒤 POSIX/BSD 소켓을 C++ 객체 수명과 이벤트 루프에 연결합니다.

## 준비 상태 통지에서 입출력까지

```text
커널 준비 상태 통지 → 이벤트 루프 → fd로 Connection 조회
                                         ├→ recv → 입력 버퍼
                                         └→ 출력 버퍼 → send

연결 삭제 → 폴러 등록 해제 → fd 닫기
```

준비 상태는 작업 완료를 뜻하지 않습니다. 지금 시스템 호출을 시도하면 블로킹 없이 진행될 가능성이 있다는 통지입니다.

## 줄 단위 서버로 이벤트 루프 확인

[논블로킹 줄 단위 서버 실습](../../exercises/02-cpp98-systems/networking/line-server/README.md)은 블로킹 단일 연결 서버에서 시작해 플랫폼별 폴러를 사용하는 논블로킹 참조 서버까지 제공합니다.

```sh
cd exercises/02-cpp98-systems/networking/line-server
make observe
```

위 명령은 저장소 루트에서 실행합니다. `make observe`는 참조 서버를 소스 미열람 상태에서 실행하는 선택적 블랙박스 관찰 도구입니다. 워크스페이스의 `skeleton/`을 구현한 뒤 저장소 루트에서 다음 명령으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=networking/line-server
```

학습자 구현 검증을 통과한 뒤에만 참조 구현과 비교합니다. 참조 구현의 `stress`, `backpressure`, `leak-check`는 저장소 전체 검증에서 별도로 실행합니다. 테스트는 실제 TCP 연결을 열어 분할 프레임, 여러 프레임의 병합, 동시 클라이언트, 느린 수신자, `QUIT` 후 EOF와 `SIGTERM` 종료를 검사합니다. Linux에서는 `epoll`, macOS/BSD에서는 `kqueue` 구현을 선택합니다.

---

## 1. 파일 디스크립터를 자원으로 관리하기

프로그램에서 파일 디스크립터는 작은 정수로 보이지만 실제 소켓 상태와 버퍼는 커널이 관리합니다. 파일 디스크립터를 닫지 않으면 커널 자원이 누수됩니다. 닫힌 번호는 곧 다른 파일이나 소켓에 재사용될 수 있으므로, 오래된 번호를 보관한 코드가 전혀 다른 자원을 조작할 수도 있습니다.

각 파일 디스크립터에 대해 다음을 답할 수 있어야 합니다.

- 소유자는 누구입니까?
- 어느 시점에 소유권을 얻습니까?
- 누가 `close`합니까?
- 소유자가 컨테이너에서 제거될 때 어떤 순서로 정리합니까?
- 이벤트 백엔드 등록이 파일 디스크립터 수명보다 오래 남지 않습니까?

## 2. 수신 대기 소켓 생성 순서

```text
socket
→ 파일 디스크립터 플래그 설정
→ 소켓 옵션 설정
→ bind
→ listen
→ 이벤트 백엔드 등록
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

        // 주소 구성, bind, listen
        return fd;
    }
    catch (...)
    {
        ::close(fd);
        throw;
    }
}
```

원시 파일 디스크립터가 RAII 객체에 들어가기 전의 짧은 구간에는 수동 정리가 필요합니다. 가능하면 `socket`이 성공한 직후 `UniqueFd`로 감싸고, 최종 소유자에게 넘길 때만 `release`합니다.

`SO_REUSEADDR`의 정확한 의미는 운영체제마다 차이가 있습니다. 포트 공유나 다중 리스너를 자동으로 허용하는 옵션으로 해석하지 않습니다.

## 3. 주소 구조체와 바이트 순서

IPv4 주소는 `sockaddr_in`에 저장합니다.

```cpp
sockaddr_in address;
std::memset(&address, 0, sizeof(address));
address.sin_family = AF_INET;
address.sin_port = htons(port);

const int converted =
    ::inet_pton(AF_INET, addressText, &address.sin_addr);
if (converted == 0)
    throw std::invalid_argument("IPv4 주소 형식이 올바르지 않습니다");
if (converted == -1)
    throw SystemError("inet_pton", errno);
```

- 포트는 `htons`로 네트워크 바이트 순서로 변환합니다.
- `inet_pton`의 형식 오류 `0`과 시스템 오류 `-1`을 구분합니다.
- 범용 소켓 함수에는 `sockaddr*`로 변환해 전달합니다.
- 상대 주소를 받을 때는 충분히 큰 `sockaddr_storage`를 사용할 수 있습니다.

```cpp
if (::bind(fd, reinterpret_cast<sockaddr *>(&address),
           sizeof(address)) == -1)
    throw SystemError("bind", errno);
```

## 4. 연결 수락과 소유권 이전

수신 대기 파일 디스크립터는 새 연결을 받는 소켓입니다. `accept`는 각 클라이언트를 위한 새 파일 디스크립터를 반환합니다.

```cpp
while (true)
{
    sockaddr_storage peer;
    socklen_t length = sizeof(peer);
    int client = ::accept(listener,
        reinterpret_cast<sockaddr *>(&peer), &length);

    if (client >= 0)
    {
        // 클라이언트 fd를 설정하고 최종 소유자에게 인계합니다.
        continue;
    }

    const int error = errno;
    if (error == EINTR)
        continue;
    if (error == EAGAIN || error == EWOULDBLOCK)
        break;

    reportSystemError("accept", error);
    break;
}
```

준비 상태 한 번에 대기 중인 연결이 여러 개일 수 있으므로 `EAGAIN` 또는 `EWOULDBLOCK`이 나올 때까지 반복해서 수락합니다. 수락한 파일 디스크립터의 논블로킹·실행 시 닫기 플래그는 플랫폼 규칙에 의존하지 말고 명시적으로 설정합니다. 설정이나 컨테이너 삽입이 실패하면 해당 파일 디스크립터를 반드시 닫아야 합니다.

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

`F_SETFL`에 `O_NONBLOCK`만 전달하면 다른 상태 플래그를 잃을 수 있습니다. Linux의 `accept4`는 수락과 플래그 설정을 한 번에 처리할 수 있지만, 이식 가능한 경로가 필요하면 `accept` 뒤 `fcntl`을 사용합니다.

## 6. 시스템 호출 결과 분류

논블로킹 I/O의 `-1`이 항상 치명적인 오류는 아닙니다.

| 결과 | 의미 | 일반적인 처리 |
|---|---|---|
| `> 0` | 처리한 바이트 수 | 오프셋과 버퍼 상태 변경 |
| `recv`에서 `== 0` | 상대가 쓰기 방향을 정상 종료 | EOF 상태 기록 |
| `-1`, `EINTR` | 시그널로 중단 | 종료 상태를 확인한 뒤 재시도 |
| `-1`, `EAGAIN/EWOULDBLOCK` | 지금은 진행 불가 | 준비 상태 대기로 복귀 |
| 그 외 `-1` | 실제 오류 | 오류 기록 후 연결 종료 요청 |

`errno`는 실패 직후 지역 변수에 복사합니다. 로그 문자열을 만드는 등 다른 함수를 호출한 뒤에는 값이 바뀔 수 있습니다.

## 7. 부분 읽기와 입력 버퍼

TCP는 메시지 경계를 보존하지 않습니다. 한 번의 `recv`는 다음 중 어느 형태든 반환할 수 있습니다.

```text
명령의 일부
명령 하나
여러 명령
여러 명령과 마지막 명령의 일부
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

        const int error = errno;
        if (error == EINTR)
            continue;
        if (error == EAGAIN || error == EWOULDBLOCK)
            return result;
        return ReadResult::error(error);
    }
}
```

프로토콜 프레이밍은 별도 계층이 `input_`에서 완성된 프레임만 꺼내도록 합니다. 소켓 계층이 명령 문법이나 HTTP 구조까지 알게 하지 않습니다.

입력 상한을 넘긴 뒤에도 계속 읽으면 메모리 사용을 제한할 수 없습니다. 상한 초과 시 오류 응답 가능 여부와 연결 종료 시점을 명시합니다.

## 8. 부분 쓰기와 출력 버퍼

`send`가 요청한 바이트를 전부 전송한다는 보장은 없습니다.

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
        if (count == 0)
            return WriteResult::noProgress();

        const int error = errno;
        if (error == EINTR)
            continue;
        if (error == EAGAIN || error == EWOULDBLOCK)
            return WriteResult::wouldBlock();
        return WriteResult::error(error);
    }

    output_.clear();
    writeOffset_ = 0;
    return WriteResult::complete();
}
```

전송한 바이트 수만큼 오프셋을 전진시킵니다. 매번 이미 보낸 앞부분을 `erase`하면 큰 버퍼에서 반복적인 이동 비용이 생길 수 있습니다. 오프셋을 유지하고 충분히 진행됐을 때만 버퍼를 압축합니다.

전송할 길이가 0보다 큰데도 `send`가 0을 반환하면 같은 루프에서 무한히 재시도하지 말고 진행 없음으로 별도 처리합니다.

## 9. 백프레셔

상대가 데이터를 읽지 않으면 커널 송신 버퍼가 차고 애플리케이션 출력 버퍼가 계속 커질 수 있습니다. 이를 방치하면 느린 클라이언트 몇 개가 프로세스 메모리를 소모합니다.

연결별 상한을 둡니다.

```text
pending output <= maxPendingBytes
```

상한을 넘었을 때의 정책을 정합니다.

- 오류 응답을 추가할 여유가 있으면 응답 후 종료
- 즉시 연결 종료
- 읽기 감시를 중지하고 출력을 우선 처리

정책은 프로토콜과 서비스 요구에 따라 달라질 수 있지만 버퍼가 무제한으로 증가해서는 안 됩니다. 읽기 감시를 끄는 정책을 사용한다면 입력 정체와 제한 시간도 함께 정의합니다.

## 10. 준비 상태 통지의 의미

읽기 준비 상태는 블로킹 없이 읽을 수 있을 가능성을 뜻할 뿐, 한 메시지가 완성됐다는 뜻이 아닙니다. 쓰기 준비 상태도 출력 전체를 전송할 수 있다는 보장이 아닙니다.

준비 상태 이벤트를 받은 뒤에도 실제 시스템 호출 결과를 `EINTR`, `EAGAIN`, EOF와 실제 오류로 다시 분류해야 합니다.

## 11. `select`, `poll`, `epoll`, `kqueue`

| API | 범위 | 모델 |
|---|---|---|
| `select` | POSIX | 파일 디스크립터 집합을 매번 전달하며 번호 상한이 있을 수 있음 |
| `poll` | POSIX | `pollfd` 배열을 매번 전달 |
| `epoll` | Linux | 관심 파일 디스크립터를 커널에 등록하고 준비 이벤트만 수신 |
| `kqueue` | BSD/macOS | 읽기·쓰기 등 필터를 개별 등록 |

표면 API는 다르지만 애플리케이션이 필요한 공통 책임은 작습니다.

```text
add(fd, interests)
update(fd, interests)
remove(fd)
wait(timeout)
```

운영체제별 이벤트 플래그와 등록 방식은 백엔드 안에 가둡니다. 연결과 애플리케이션 객체가 `EPOLLIN`, `EVFILT_READ` 같은 상수를 직접 다루지 않게 합니다.

## 12. 레벨 트리거와 에지 트리거

### 레벨 트리거

준비 상태가 유지되면 다음 `wait`에서도 다시 통지됩니다. 한 번에 모두 처리하지 못해도 다음 기회가 있어 첫 구현에 적합합니다.

### 에지 트리거

준비되지 않은 상태에서 준비된 상태로 바뀌는 경계를 중심으로 통지합니다. 이벤트를 받았을 때 `EAGAIN`까지 읽거나 쓰지 않으면 데이터가 남아 있어도 다음 통지를 받지 못할 수 있습니다.

첫 구현은 레벨 트리거로 시작합니다. 레벨 트리거에서도 한 이벤트에 가능한 만큼 처리하면 시스템 호출과 이벤트 반복 횟수를 줄일 수 있습니다.

## 13. 이벤트 루프의 불변식

이벤트 루프는 다음 조건을 유지해야 합니다.

```text
등록된 각 클라이언트 fd에는 정확히 하나의 Connection 소유자가 있습니다.
닫힌 fd는 폴러와 연결 테이블에 남지 않습니다.
Connection 삭제 뒤 콜백이나 이벤트가 옛 객체를 사용하지 않습니다.
보낼 데이터가 없으면 쓰기 관심 상태를 등록하지 않습니다.
한 반복에서 같은 fd를 두 번 닫지 않습니다.
```

기본 루프는 다음과 같습니다.

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

이벤트 목록을 순회하는 동안 연결 컨테이너에서 객체를 즉시 지우면, 같은 대기 결과에 포함된 이후 이벤트나 현재 콜백이 삭제된 객체를 참조할 수 있습니다. 종료 요청만 표시하고 안전한 지점에서 모아 처리하는 방식이 단순합니다.

## 14. 연결 객체의 책임

`Connection`은 소켓 파일 디스크립터와 연결별 바이트 상태를 소유합니다.

```text
fd
입력 버퍼
출력 버퍼와 쓰기 오프셋
입력·출력 상한
상대 EOF 여부
종료 요청 여부
마지막 활동 시각
```

다음 책임은 분리합니다.

- 프로토콜 파싱과 명령 처리
- 전체 연결 테이블
- 이벤트 백엔드
- 서버 전체 설정

연결이 읽고 쓸 바이트를 관리하고 파서가 바이트의 메시지 의미를 관리하면, 프로토콜을 바꿔도 이벤트 루프의 수명 규칙은 유지됩니다.

## 15. 필요한 동안만 쓰기 준비 상태 감시하기

TCP 소켓은 대개 쓰기 가능 상태입니다. 보낼 데이터가 없는데 쓰기 이벤트를 계속 등록하면 대기 함수가 즉시 반환하는 바쁜 반복이 생길 수 있습니다.

```cpp
unsigned int desired = Interest::READ;
if (connection.hasPendingOutput())
    desired |= Interest::WRITE;

poller_.update(connection.fd(), desired);
```

- 출력 큐가 비어 있다가 데이터가 생김 → 쓰기 관심 상태 추가
- `flush`가 모두 완료됨 → 쓰기 관심 상태 제거
- 전송 완료 뒤 닫을 상태 → 필요에 따라 읽기를 끄고 쓰기만 유지

관심 상태 계산을 한 함수에 모으고 연결 상태가 바뀐 뒤 일관되게 호출합니다.

## 16. `SIGPIPE`와 `EINTR`

닫힌 소켓에 `send`하면 `SIGPIPE`가 전달될 수 있으며 기본 동작은 프로세스 종료입니다.

일반적인 대응은 다음과 같습니다.

- 프로세스에서 `SIGPIPE` 무시
- Linux에서 `MSG_NOSIGNAL` 사용
- macOS 등에서 `SO_NOSIGPIPE` 설정

플랫폼별 차이는 `sendFlags`나 소켓 설정 보조 함수에 가둡니다.

`EINTR`은 시그널 처리로 시스템 호출이 중단됐다는 뜻입니다. 일반 I/O는 다시 시도할 수 있지만, 종료 시그널로 이벤트 대기를 깨우는 설계라면 재시도하기 전에 종료 플래그를 확인합니다.

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
        if (fd_ == fd)
            return;
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

C++98에는 이동 의미론이 없으므로 소유권 전달을 `release`, `reset`, `swap` 같은 명시적인 동작으로 제한합니다. 함수가 원시 파일 디스크립터를 반환하면 인계 직후 소유자 객체에 넣습니다.

소멸자에서는 `close` 실패를 호출자에게 보고할 수 없습니다. 업무상 닫기 성공 확인이 필요한 자원이라면 명시적인 종료 함수를 별도로 두고, 소멸자는 남은 자원을 정리합니다. `close`가 `EINTR`을 반환했다고 같은 숫자를 무조건 다시 닫으면 이미 재사용된 파일 디스크립터를 닫을 위험이 있으므로 대상 운영체제의 규칙을 확인합니다.

## 18. 공통 `Poller` 인터페이스

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

Linux 백엔드는 파일 디스크립터 하나의 관심 비트 마스크를 `epoll_ctl`로 변경합니다. `kqueue` 백엔드는 읽기와 쓰기 필터를 별도로 추가·삭제합니다. 이 차이는 백엔드 구현 안에 머물러야 합니다.

오류·종료 이벤트는 읽기 또는 쓰기 이벤트와 함께 올 수 있습니다. 이벤트 비트만 보고 즉시 삭제하기보다 남은 입력, `SO_ERROR`, 상대 EOF와 출력 정책을 일관된 순서로 처리합니다.

## 19. 연결 삭제와 콜백 수명

위험한 흐름은 다음과 같습니다.

```text
Connection 콜백 호출
→ 콜백이 server.disconnect(fd) 호출
→ 연결 테이블에서 Connection 삭제
→ 원래 함수가 삭제된 Connection을 계속 사용
```

다음 방법으로 방지할 수 있습니다.

- 콜백 중에는 `closeRequested`만 표시
- 현재 이벤트 반복이 끝난 뒤 지연 삭제
- 삭제 전에 이후에 필요한 데이터를 값으로 복사
- 콜백이 끝날 때까지 소유 객체의 파괴를 미루는 별도 수명 경계 사용

비소유 원시 포인터나 참조를 사용하는 동안 소유자를 삭제할 수 있는 호출을 사이에 두지 않습니다.

## 20. 이벤트 루프에 타이머 추가하기

유휴 제한 시간과 작업 제한 시간을 위해 연결별 마지막 활동 시각이나 기한을 기록합니다. 연결 수가 작다면 대기 제한 시간마다 전체 연결을 순회하는 방식으로 시작해도 충분합니다.

확장 후보는 다음과 같습니다.

- 최소 힙 기반 타이머 큐
- Linux `timerfd`
- `kqueue`의 `EVFILT_TIMER`

자료구조를 복잡하게 만들기 전에 정확성을 확보하고 실제 연결 수와 타이머 변경 빈도를 측정합니다.

---

## 단계형 실습: 논블로킹 줄 서버

### 1단계: 블로킹 단일 연결

`socket → bind → listen → accept` 순서로 한 클라이언트의 줄을 에코합니다. 이 단계에서는 이벤트 루프를 만들지 않습니다.

검증 항목:

- 서버 재시작 시 다시 `bind`할 수 있음
- 클라이언트 EOF 처리
- 오류 경로에서 파일 디스크립터 정리

### 2단계: `UniqueFd`

리스너와 클라이언트 파일 디스크립터를 RAII 소유자에 넣습니다. 중간 예외를 의도적으로 만들고 파일 디스크립터가 닫히는지 확인합니다.

### 3단계: 논블로킹과 `Poller` 한 백엔드

현재 운영체제의 `epoll` 또는 `kqueue` 하나만 구현합니다. 리스너 준비 상태와 여러 클라이언트를 처리합니다.

### 4단계: 연결 버퍼

한 번에 여러 줄이 들어오는 경우와 한 줄이 여러 번에 나뉘어 들어오는 경우를 모두 처리합니다.

```text
send #1: "PUT a"
send #2: " 1\nGET a\n"
```

### 5단계: 부분 쓰기와 백프레셔

연결별 출력 버퍼, 오프셋과 쓰기 관심 상태 전환을 추가합니다. 느린 클라이언트를 재현해 출력 상한이 작동하는지 확인합니다.

### 6단계: 안전한 종료

콜백에서는 닫기 요청만 표시하고 이벤트 반복 끝에서 삭제합니다. 상대 EOF, 프로토콜 오류, 송신 오류와 서버 중지 경로를 각각 테스트합니다.

### 7단계: 두 번째 백엔드

공통 `Poller` 인터페이스를 유지한 채 다른 플랫폼 백엔드를 추가합니다. 애플리케이션 코드에 운영체제별 상수가 노출되지 않는지 확인합니다.

## 테스트 항목

- 리스너 생성 단계별 실패
- 수락 뒤 플래그 설정 실패
- `socketpair`를 이용한 부분 읽기와 쓰기
- 한 번의 `send`에 여러 프레임
- 한 프레임을 여러 번의 `send`로 분할
- 상대 EOF
- 출력 버퍼 상한
- 콜백 중 닫기 요청
- 여러 클라이언트의 상태 독립성
- 반복 연결·종료 뒤 파일 디스크립터 수 증가 여부
- 종료 시그널 뒤 이벤트 대기 종료

## 논블로킹 소켓에서 자주 발생하는 오류

- 수락한 파일 디스크립터를 설정 실패 경로에서 닫지 않습니다.
- `recv == 0`을 `EAGAIN`처럼 처리합니다.
- 한 번의 `recv`가 메시지 하나라고 가정합니다.
- `send` 반환값이 요청 길이와 항상 같다고 가정합니다.
- 출력이 없는데 쓰기 이벤트를 계속 등록합니다.
- 에지 트리거 방식에서 `EAGAIN`까지 소진하지 않습니다.
- 파일 디스크립터를 닫기 전에 백엔드 등록을 정리하지 않습니다.
- 콜백이 연결을 삭제한 뒤 원래 함수가 계속 접근합니다.
- `SIGPIPE` 대응 없이 닫힌 상대에게 씁니다.
- 하나의 원시 파일 디스크립터를 여러 객체가 소유한다고 가정합니다.

## 다른 비동기 런타임과 비교

Node.js, Java NIO, Netty, Rust Tokio와 Python `asyncio`는 API가 다르지만 같은 상태를 관리합니다.

```text
연결별 입력·출력 상태
준비 상태 또는 완료 이벤트
부분 I/O
백프레셔
제한 시간
연결 수명
```

프레임워크가 이벤트 루프를 감추더라도 느린 클라이언트, 취소와 연결 종료를 처리하는 규칙은 여전히 애플리케이션 설계에 남습니다.

## 소켓과 이벤트 루프 점검

- 리스너와 각 클라이언트 파일 디스크립터의 소유자를 지목할 수 있습니까?
- `recv`의 성공, EOF, `EINTR`, `EAGAIN`과 실제 오류 경로를 설명할 수 있습니까?
- 읽기 준비 상태가 완성된 메시지를 뜻하지 않는 이유는 무엇입니까?
- 쓰기 관심 상태를 항상 등록하면 어떤 문제가 생깁니까?
- 출력 버퍼 상한이 필요한 이유와 초과 정책은 무엇입니까?
- 이벤트 반복 중 연결 삭제를 지연하는 이유는 무엇입니까?
- `epoll`과 `kqueue`의 차이가 애플리케이션 계층에 노출되지 않습니까?
