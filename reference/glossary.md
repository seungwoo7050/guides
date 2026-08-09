# 용어

## Asset

보호 가치가 있는 데이터·identity·capability·artifact·서비스 상태와 운영 증거입니다. 구성요소 이름만이 아니라 어떤 상태를 보호하는지 포함합니다.

## Security property

시스템이 유지해야 하는 보안 상태입니다. confidentiality, integrity, availability 외에도 authorization, isolation, accountability, provenance와 recoverability가 포함될 수 있습니다.

## Invariant

허용된 모든 상태 전이 뒤에도 유지돼야 하는 조건입니다. 예: 한 tenant의 worker credential은 다른 tenant prefix를 읽을 수 없습니다.

## Threat

특정 capability를 가진 행위자가 전제 조건에서 경계를 이용해 보호할 상태를 원하지 않는 상태로 바꿀 가능성입니다.

## Weakness

설계·구현·운영의 결함 또는 통제 부족입니다. 실제 공격 전제와 영향이 확인되기 전에는 취약점으로 확정하지 않습니다.

## Exposure

공격자가 asset·entry point·identity에 도달할 수 있는 정도입니다.

## Vulnerability

현재 환경에서 공격 전제와 보안 영향이 성립하는 검증된 약점입니다.

## Finding

평가 결과를 추적하는 단위입니다. 후보가 사실인지 나타내는 `validation_status`, 처리 방향인 `treatment`, 업무 진행 상태인 `lifecycle_status`를 분리합니다. 위험 수용은 검증 상태가 아니라 confirmed finding에 대한 `treatment: accept`이며, `duplicate_of`도 별도 관계입니다.

## Precondition

공격 단계가 실행되기 전에 필요한 권한·구성·데이터·시간 상태입니다.

## Postcondition

한 단계 뒤 공격자가 새로 얻거나 시스템이 잃은 capability·상태입니다.

## Attack surface

신뢰 경계를 넘는 entry point, identity, data parser, dependency, operation과 recovery 경로의 집합입니다.

## Attack path

여러 단계의 precondition과 postcondition이 연결돼 특정 asset 영향에 도달하는 경로입니다.

## Choke point

여러 공격 경로가 공통으로 의존하는 통제·identity·flow입니다. 한 choke point를 막아도 우회 경로가 남는지 확인합니다.

## Evidence

보안 주장이나 반증을 지지하는 관찰 가능한 근거입니다. source, time, environment, collection method와 limitation이 필요합니다.

## Oracle

테스트 결과가 허용 상태인지 거부 상태인지 독립적으로 판정하는 기준입니다.

## Assurance

보안 주장이 어느 범위에서 얼마나 신뢰할 수 있는지를 만드는 evidence의 집합입니다. 검사 도구를 실행했다는 사실만을 뜻하지 않습니다.

## Compensating control

원래 통제를 즉시 구현할 수 없을 때 위험을 제한하는 임시 통제입니다. owner·expiry·재검토 조건이 필요합니다.

## Containment

사건의 확산과 추가 영향을 제한하는 조치입니다. root cause 제거와 동일하지 않습니다.

## Eradication

침해 원인, 손상된 identity·artifact·persistence와 유사 경로를 제거하는 단계입니다.

## Recovery

신뢰 가능한 원본에서 기능과 보안 상태를 복원하고 강화 관찰로 안정성을 확인하는 단계입니다.

## Residual risk

현재 통제와 계획된 수정 뒤에도 남는 위험입니다. 누가 어떤 기간과 근거로 수용하는지 기록합니다.

## Evidence age

증거가 현재 build·policy·environment를 얼마나 최신으로 대표하는지 나타냅니다. 관련 변경이 생기면 오래된 증거가 될 수 있습니다.

## Rules of Engagement

평가의 허가 범위, 허용·금지 행동, 예산, 중단 조건, 연락과 evidence 처리 계약입니다.
