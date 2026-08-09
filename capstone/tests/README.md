# Capstone public tests

이 디렉터리의 검사는 capstone starter가 기대하는 공개 API와 초기 milestone의 핵심 계약을 보여 줍니다. 완성된 protocol 검증 전체가 아닙니다.

```sh
CAPSTONE_ROOT=.workspace/replicated-kv \
  python3 -m unittest discover -s capstone/tests -v
```

테스트를 수정해 통과시키지 않습니다. 구현이 진행되면 자신의 fault schedule, every-step invariant와 history checker를 별도 테스트로 추가합니다.
