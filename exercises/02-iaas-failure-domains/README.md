# 02. IaaS resource와 failure domain

## 목적

가상의 공개 API를 resource inventory와 failure domain으로 복원하고, instance·zone·state·network·cleanup 실패 뒤 무엇이 남는지 작성합니다.

## 입력

[`inputs/system.md`](inputs/system.md)를 사용합니다.

## 결과물

`architecture-review.md`에 다음을 포함합니다.

- resource inventory와 owner
- state classification
- network exposure
- failure domain map
- zone loss 시 남은 capacity
- backup·restore
- scaling과 quota
- failure injection과 evidence
- cleanup 순서

## 사람 검토 질문

1. instance 수와 failure independence를 혼동하지 않았습니까?
2. database·object·log·key의 수명을 분리했습니까?
3. zone 하나가 사라졌을 때 실제 처리 capacity를 계산했습니까?
4. control plane success와 application readiness를 구분했습니까?
5. 삭제 뒤 volume·address·snapshot·log·key가 어떻게 되는지 적었습니까?
