# 용어집

## Availability zone

region 안의 상대적으로 독립된 failure domain. 공급자별 물리·network·control plane 범위가 다르므로 실제 contract를 확인한다.

## Control plane

resource의 생성·설정·policy·배치를 변경하는 관리 경로.

## Data plane

사용자 request, object read, database query처럼 실제 workload와 data를 처리하는 경로.

## Durable state

process나 instance가 사라져도 보존해야 하는 정본 상태.

## Elasticity

수요에 따라 resource를 늘리고 줄이는 능력. 무한 capacity나 즉시 scaling을 뜻하지 않는다.

## Entitlement

현재 tenant가 특정 feature를 사용할 수 있는지 결정한 상태.

## FaaS

event 또는 request 단위로 function을 실행하는 managed/serverless compute 모델. NIST의 IaaS·PaaS·SaaS와 동일한 분류 축으로 단순 취급하지 않는다.

## Failure domain

하나의 사건으로 함께 영향을 받을 수 있는 resource 집합.

## IaaS

소비자가 compute·network·storage를 조합하고 OS·runtime·application을 더 많이 관리하는 service model.

## Idempotency

같은 command 또는 event를 여러 번 처리해도 최종 업무 효과가 한 번과 같은 성질.

## Managed service

공급자가 내부 운영 일부를 수행하고 소비자에게 제한된 control surface와 service contract를 제공하는 capability.

## Measured service

사용량을 측정·보고하고 allocation 또는 billing에 사용할 수 있는 cloud 특성.

## Noisy neighbor

공유 resource에서 한 tenant 또는 workload가 다른 사용자의 성능·capacity에 영향을 주는 현상.

## PaaS

application을 배포·실행하는 platform capability를 service로 제공하는 모델.

## Quota

resource·request·storage·concurrency·business usage의 허용 상한.

## Region

공급자가 cloud resource를 제공하는 지리적·운영 범위. 정확한 failure independence는 공급자 contract를 확인한다.

## Resource pooling

공급자가 공유 pool에서 resource를 소비자에게 동적으로 할당하는 cloud 특성.

## SaaS

완성된 application capability를 service로 제공하는 모델. SaaS 공급자에게 tenant·product·support·billing 상태가 생긴다.

## Serverless

소비자가 개별 server instance lifecycle을 직접 관리하지 않고 request·event·managed capacity 단위로 workload를 실행하는 운영 모델.

## Tenant

데이터·설정·권한·사용량·계약을 공유하는 고객 경계. 사용자 한 명이나 database schema와 반드시 같지 않다.

## Workload identity

VM·container·function·job 같은 실행 주체가 다른 resource에 접근할 때 사용하는 identity.
