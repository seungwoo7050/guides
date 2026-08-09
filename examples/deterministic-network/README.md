# 결정적 network scheduler 예제

실제 socket과 thread 대신 message delivery를 명시적인 event로 관리합니다. 같은 initial state와 action schedule은 같은 trace와 digest를 만들어야 합니다.

## 실행

```sh
python3 examples/deterministic-network/simulation.py
python3 examples/deterministic-network/simulation.py \
  examples/deterministic-network/schedule.json
```

## 제공하는 경계

- virtual time
- 안정적인 event sequence 번호
- message send·drop·duplicate·deliver
- node crash·restart
- 명시적인 action schedule
- canonical JSON trace와 SHA-256 digest

이 예제는 실제 TCP, kernel buffer, disk write ordering이나 process pause를 재현하지 않습니다. capstone에서는 protocol state를 같은 scheduler 위에 연결하고, 실제 runtime 검증은 별도 통합 계층에 둡니다.
