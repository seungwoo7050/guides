# 시스템, identity와 secret 경계 실패

시스템 보안은 `root`와 일반 사용자만 구분하는 문제가 아닙니다. process, service, container, CI job, operator와 automated worker가 각각 어떤 identity와 resource scope를 가지는지 추적해야 합니다.

Unix 객체와 관찰 방법은 `unix-systems`, process·memory·isolation 원리는 `operating-systems`, host·network 운영은 `web-infra`가 소유합니다. 공통 workload identity·secret delivery·policy 경로를 제품으로 제공하는 일은 `platform-engineering`의 범위입니다. 이 장은 그 구현 기초를 반복하지 않고, 해당 상태와 권한이 취약점·권한 상승·내부 이동의 공격 경로로 연결되는 조건을 다룹니다.

## 1. 실행 identity

각 workload에 다음을 적습니다.

```text
실행 user·group
process namespace
filesystem read·write 범위
network reachability
inbound caller
outbound dependency
available credential
kernel·runtime capability
log·audit destination
```

애플리케이션 기능과 무관한 권한이 ambient하게 제공되면 하나의 application bug가 더 큰 system capability로 변합니다.

## 2. privilege boundary

privilege 상승은 exploit 하나만 뜻하지 않습니다.

- 잘못된 file·directory mode
- writable service unit·startup script·binary path
- broad `sudo` 또는 helper command
- privileged socket·daemon API 접근
- setuid·capability·device 접근
- host mount와 container runtime socket
- cloud metadata와 workload credential
- admin API에 접근 가능한 network·identity

검증할 때 “현재 user가 root가 될 수 있는가”보다 다음을 묻습니다.

```text
현재 capability가 어떤 protected action으로 바뀔 수 있는가?
그 전이에 필요한 파일·process·credential·network는 무엇인가?
```

## 3. service identity와 delegation

service가 사용자를 대신해 다른 service를 호출할 때 identity 모델을 선택해야 합니다.

### End-user identity 전달

장점:

- 원래 subject와 resource scope를 유지하기 쉽습니다.

주의:

- 원래 user token을 그대로 전달할지, downstream 전용 token exchange·제약된 delegation을 사용할지
- token audience·lifetime·delegation chain과 각 hop의 issuer
- downstream service가 upstream header를 무조건 신뢰하지 않는지
- user token을 불필요한 service에 전파하지 않는지
- 호출 workload와 delegated end user를 각각 audit할 수 있는지

### Service identity 사용

장점:

- workload authentication과 service ownership이 명확합니다.

주의:

- 사용자의 resource scope가 사라질 수 있음
- broad service token으로 confused deputy 문제가 생길 수 있음
- job·tenant·resource context의 출처·무결성을 별도로 검증해야 함
- delegated context가 없거나 만료됐을 때 service privilege로 fallback하지 않는지

좋은 설계는 authenticated calling service, delegated actor와 effective subject를 구분하고, downstream이 audience·delegation·resource context를 함께 검증합니다. caller가 제공한 평문 identity header는 신뢰 경계가 아니며, token exchange도 새 token의 scope가 원래 actor와 calling service의 허용 범위를 넘어가지 않아야 합니다.

## 4. 최소 권한을 구체화하기

“read-only”도 충분히 구체적이지 않을 수 있습니다.

```text
어느 resource collection인가?
어느 tenant·prefix인가?
어떤 field·version인가?
어느 시간 동안인가?
어느 network·workload에서 사용할 수 있는가?
몇 번 사용할 수 있는가?
```

작업 단위 token은 가능하면 다음을 가집니다.

- 짧은 expiry
- 명확한 audience
- task·tenant·resource scope
- 발급 이유와 parent identity
- revoke 방식과 각 verifier에 반영되는 최대 지연
- 사용 audit

## 5. credential과 secret의 차이

secret은 기밀 data이고, credential은 identity 또는 권한을 증명하는 데 사용됩니다. 모든 secret이 credential은 아니지만 credential 노출은 즉시 capability 증가로 이어질 수 있습니다.

lifecycle:

```text
generate
→ store
→ distribute
→ use
→ observe without disclosure
→ rotate
→ revoke
→ destroy
```

각 단계의 owner와 evidence를 적습니다.

여기서 revoke는 **관련 verifier가 이후 제시된 credential을 더 이상 받아들이지 않게 만드는 상태 전이**입니다. 이미 복사된 secret bytes를 회수하거나, 과거에 만든 session·파생 credential·완료된 action을 되돌린다는 뜻이 아닙니다. self-contained token은 expiry 전까지 verifier가 issuer state를 조회하지 않으면 즉시 revoke되지 않습니다. 짧은 lifetime, introspection·denylist, session invalidation, signing key와 trust store 전환 가운데 실제 방식을 정합니다. cache까지의 최대 반영 지연을 측정하고, 관찰할 수 없는 disconnected verifier는 남은 acceptance window라는 한계로 기록합니다.

## 6. secret가 새는 경로

- source·configuration·example
- build argument·layer·artifact
- environment와 process inspection
- command line·shell history
- debug endpoint·crash dump
- application log·trace·error response
- CI output·test report
- backup·snapshot
- client bundle·mobile package
- support ticket·chat·clipboard

scanner가 secret pattern을 찾았다고 실제 유효 credential로 단정하지 않고, 반대로 현재 invalid하다고 과거 영향이 없었다고 단정하지 않습니다.

## 7. rotation은 문자열 교체가 아닙니다

안전한 rotation state machine:

```text
새 credential 생성
→ 제한된 consumer에 배포
→ 새 credential로 readiness 확인
→ traffic 전환
→ 이전 credential 사용 감시
→ 이전 credential revoke
→ cache·session·artifact 정리
→ audit와 rollback 정보 기록
```

하나의 shared secret을 모든 consumer가 동시에 바꾸는 방식은 부분 실패와 rollback 문제를 만듭니다. rotation 완료는 문자열이 바뀐 시점이 아니라 새 credential readiness, 범위 안 verifier의 이전 credential 거절, 잔여 사용 관측과 파생 session 처리까지 확인한 시점입니다. 확인할 수 없는 verifier나 copy는 완료 근거가 아니라 알려진 한계로 남깁니다. signing key를 폐기하면 관련 없는 token까지 무효화될 수 있으므로 blast radius와 복구 경로도 기록합니다.

## 8. container와 sandbox 경계

container는 자동으로 강한 security boundary가 아닙니다. 다음이 경계를 약화합니다.

- privileged mode
- broad Linux capability
- host PID·network namespace
- writable host mount
- container runtime socket
- container 안의 UID 0과 writable root filesystem
- host secret·cloud metadata 접근
- unbounded process·memory·disk·network

container 안의 UID 0은 namespace와 capability가 제한돼 있다면 곧바로 host root와 같지 않습니다. 반대로 non-root 실행만으로 host 격리가 증명되지도 않습니다. broad capability, host mount, runtime socket, shared namespace, 취약한 kernel 또는 control-plane credential이 있으면 container identity가 host·cluster capability로 이어질 수 있습니다. 평가할 때 escape 기법을 먼저 찾기보다 application compromise 뒤 실제 namespace·capability·mount·socket·credential을 관찰해 그 전이를 증명합니다.

## 9. internal network는 trust가 아닙니다

internal service도 authentication·authorization·input validation이 필요합니다.

- workload identity 없이 source IP만 신뢰
- gateway가 붙인 header를 direct request에서도 신뢰
- internal DNS name을 possession proof로 사용
- queue에 message를 넣을 수 있으면 모든 command를 허용
- service mesh encryption을 authorization으로 오해

network location은 하나의 signal일 수 있지만 principal과 resource decision을 대신하지 않습니다.

## 10. lateral movement

lateral movement는 host 사이 이동만이 아닙니다.

```text
user session
→ application service identity
→ queue producer
→ worker identity
→ storage credential
→ backup·registry·control plane
```

각 단계에서 얻은 capability, scope와 expiry를 기록합니다. 방어자는 다음으로 경로를 끊습니다.

- identity 분리
- audience·resource scope
- network egress·ingress policy
- short-lived token
- just-in-time privilege
- independent audit
- unusual delegation·scope 사용 탐지

## 11. emergency access

break-glass account는 평상시 편의를 위한 관리자 계정이 아닙니다.

- 별도 보관과 강한 authentication
- 사용 전 승인 또는 최소한 즉시 알림
- 짧은 수명
- 모든 action audit
- 사용 뒤 credential reset
- 정기적인 복구 drill

사용하지 못하는 emergency access도 위험하고, 항상 열려 있는 emergency access도 위험합니다.

## 12. system hardening의 한계

hardening은 attack surface와 blast radius를 줄입니다. application authorization bug를 자동으로 고치지 않습니다.

예:

- read-only filesystem은 임의 파일 쓰기를 줄이지만 다른 tenant data read를 막지 않습니다.
- non-root container는 host privilege를 낮추지만 broad storage token을 제한하지 않습니다.
- firewall은 reachability를 줄이지만 허용된 service 사이의 confused deputy를 막지 않습니다.

각 control이 끊는 attack-path edge를 명시합니다.

## 13. 이 장의 산출물

service 또는 job 하나를 선택해 다음을 작성합니다.

1. 실행 identity와 runtime privilege inventory
2. inbound caller와 outbound dependency
3. 사용 가능한 credential과 실제 scope
4. delegation model
5. ambient authority
6. credential rotation state machine
7. application compromise 뒤 가능한 lateral path
8. 경로를 끊는 prevention·detection·recovery control
9. root·container·internal network에 대한 잘못된 trust assumption
10. credential revoke의 enforcement 지점·전파 지연·남는 session
11. 각 근거가 보장하는 capability와 OS·host·platform 운영에 맡긴 범위

## 14. 완료 질문

- service identity와 end-user authorization을 왜 분리해야 합니까?
- read-only credential도 위험할 수 있는 이유는 무엇입니까?
- rotation이 부분 실패를 고려해야 하는 이유는 무엇입니까?
- container와 internal network를 완전한 trust boundary로 볼 수 없는 이유는 무엇입니까?
- hardening control이 끊는 attack-path edge를 어떻게 증명합니까?
