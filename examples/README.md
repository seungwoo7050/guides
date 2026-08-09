# 관찰 예제

각 예제는 compiler 전체가 아니라 한 개념의 상태와 실패를 작게 관찰합니다. Capstone source에 그대로 복사하기보다 input/output contract와 known-bad 검사를 비교합니다.

| 예제 | 관찰 대상 | 실행 |
|---|---|---|
| [Diagnostic renderer](diagnostic-renderer/README.md) | UTF-8 byte span을 line/column과 underline으로 변환 | `python3 examples/diagnostic-renderer/render.py --self-test` |
| [Pratt parser](pratt-parser/README.md) | binding power, associativity와 parser progress | `python3 examples/pratt-parser/pratt.py --self-test` |
| [Data-flow fixed point](dataflow-fixed-point/README.md) | CFG liveness의 join·transfer·worklist | `python3 examples/dataflow-fixed-point/dataflow.py --self-test` |
| [Bytecode verifier와 VM](bytecode-vm/README.md) | stack type verification과 실행 상태 | `python3 examples/bytecode-vm/vm.py --self-test` |

루트 `./verify.sh`는 네 예제의 self-test를 독립 process로 실행합니다.
