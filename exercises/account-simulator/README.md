# account-simulator

`account-simulator`는 여러 thread가 두 account 사이에서 동시에 transfer와 snapshot read를 수행해도 balance와 total invariants를 유지하는 C library다. Account ID 기반 canonical lock order로 반대 방향 transfer의 deadlock을 방지한다.

## Features

- account별 `pthread_mutex_t` ownership
- insufficient funds와 negative amount validation
- destination overflow 방지
- two-account transfer의 atomic commit
- self-transfer와 zero-amount transfer의 명시적 semantics
- canonical ID order를 통한 deadlock avoidance
- single-account balance와 two-account total snapshot
- concurrent worker/observer stress test

## Architecture

각 `struct account`는 balance와 mutex를 함께 소유한다. 두 account를 다루는 operation은 항상 작은 ID의 mutex부터 잠근다. 같은 object는 mutex를 한 번만 잠그며, 서로 다른 object가 같은 ID를 가지면 canonical order를 정할 수 없으므로 거부한다.

## Build

```sh
make
```

정적 library는 `build/libaccount.a`에 생성된다.

## Usage

```c
struct account left;
struct account right;
long total;

account_init(&left, 1, 1000);
account_init(&right, 2, 500);
account_transfer(&left, &right, 200);
account_total(&left, &right, &total);
account_destroy(&right);
account_destroy(&left);
```

모든 thread가 해당 account 사용을 끝내고 `join`된 뒤에만 `account_destroy`를 호출해야 한다.

## Verification

```sh
make test
make sanitize
make thread-sanitize
```

기본 test는 8 transfer workers와 2 observers를 동시에 시작한다. 모든 atomic total snapshot이 `400000`인지, balance가 음수가 되지 않는지, final balances가 보존되는지 검사한다. ThreadSanitizer target은 toolchain과 runtime이 지원되는 환경에서 data race를 추가로 검사한다.

## Design Decisions

- Account ID는 서로 다른 live account 사이에서 unique해야 한다.
- Transfer validation과 두 balance update는 두 mutex를 모두 보유한 상태에서 수행한다.
- Output parameter는 snapshot을 성공적으로 얻은 뒤에만 갱신한다.
- `account_total`은 두 개별 `account_get_balance` 호출을 합치지 않는다. 두 값 사이에 transfer가 끼어들 수 있기 때문이다.
- `account_destroy`는 synchronization primitive를 강제로 회수하지 않으며 post-join lifecycle을 전제로 한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Account lifecycle and mutex ownership | `src/account.c` |
| 2 | Canonical pair locking | `src/account.c` |
| 3 | Atomic transfer validation and commit | `src/account.c` |
| 4 | Consistent balance and total snapshots | `src/account.c` |
| 5 | Post-join destruction | `src/account.c` |

## Scope and Limitations

두 account operation만 제공하며 persistence, transaction log, condition variables, cancellation, dynamic account registry는 포함하지 않는다. Caller가 account object의 public fields를 직접 변경하면 synchronization contract가 깨진다.
