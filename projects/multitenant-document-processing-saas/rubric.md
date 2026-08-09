# Capstone 리뷰 루브릭

각 항목을 `충분`, `조건부`, `부족`으로 평가합니다.

## 책임

- stage별 provider·consumer task가 달라집니다.
- business·runtime·data·cost owner가 있습니다.

## 상태

- durable·derived·ephemeral·evidence·commercial state를 구분합니다.
- create·update·delete의 중간 상태가 있습니다.

## 실패

- instance·zone·dependency·event·quota·tenant·cost failure를 다룹니다.
- partial state와 reconciliation이 있습니다.

## 보안과 isolation

- human·workload·automation identity가 분리됩니다.
- tenant context가 request·cache·queue·export·deletion에 연결됩니다.

## evidence

- 각 주장에 test·metric·audit·restore·inventory 또는 cost evidence가 있습니다.
- evidence의 한계가 기록됩니다.

## 비용과 exit

- unit cost, budget, quota, orphan cleanup이 있습니다.
- export·migration·source deletion이 rehearsal 가능한 절차입니다.

## 결정

- 잔여 위험, owner, due date, verification과 rollback이 있습니다.
