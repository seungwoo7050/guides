# 06. 비용과 exit

## 목적

resource inventory를 business outcome과 연결해 비용 driver·budget·anomaly·cleanup을 작성하고, managed service와 SaaS를 종료하거나 교체하는 실제 exit plan을 만듭니다.

## 입력

[`inputs/inventory.md`](inputs/inventory.md)를 사용합니다.

## 결과물

`cost-and-exit-plan.md`를 완성합니다.

## 사람 검토 질문

1. idle·variable·step cost를 구분했습니까?
2. retry·log·egress·backup·orphan을 포함했습니까?
3. budget alert와 hard control을 구분했습니까?
4. export의 throughput·duration·egress cost를 estimate했습니까?
5. source deletion과 provider retention·key lifecycle을 기록했습니까?
