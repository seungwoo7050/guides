# 03. Managed service 계약

## 목적

가상의 managed database·queue·object service에서 공급자에게 이동한 작업과 소비자에게 남은 작업을 구분하고, limit·maintenance·backup·observability·exit를 계약으로 만듭니다.

## 입력

[`inputs/service-offer.md`](inputs/service-offer.md)를 사용합니다.

## 결과물

`service-contract.md`를 완성합니다.

## 사람 검토 질문

1. “공급자가 관리”를 task 단위로 분해했습니까?
2. 문서에 없는 동작을 보장으로 가정하지 않았습니까?
3. backup 생성과 restore 검증을 구분했습니까?
4. limit 초과와 version 종료가 application event로 모델링됐습니까?
5. export·migration·deletion에 data volume과 시간·비용을 포함했습니까?
