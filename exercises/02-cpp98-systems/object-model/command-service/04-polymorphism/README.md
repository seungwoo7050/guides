# 04 — 교체 가능한 핸들러

명령 분기를 `Handler` 계약과 `Router`로 바꿉니다. 호출자는 구체 핸들러의 타입과 생성 위치를 알지 않아도 됩니다.

## 구조

- `skeleton/`: 핸들러와 라우터의 골격
- `reference/`: 명령별 구체 핸들러와 소유권을 정리한 구현
- `nonvirtual_delete.cpp`: 잘못된 다형적 소멸 계약
- `test.sh`: 외부 명령 계약 검사

## 실행

```sh
make observe
make exercise-test
make test
make fail-nonvirtual
```

## 다형적 소멸 확인하기

`Handler`의 가상 소멸자를 제거합니다. 정의되지 않은 동작을 실행하지 않고 컴파일러 경고가 기반 클래스 포인터를 통한 삭제를 거부하는지 확인합니다.

## 확인할 동작

새 핸들러를 추가할 때 기존 핸들러 구현을 수정하지 않고, 라우터가 등록한 모든 핸들러를 정확히 한 번 파괴합니다.
