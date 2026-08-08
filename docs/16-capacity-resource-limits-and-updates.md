# 용량, 자원 제한과 업데이트

서비스는 코드 오류 없이도 자원이 고갈되어 실패할 수 있습니다. 메모리, CPU, disk, inode, PID, file descriptor, DB connection과 외부 API quota는 모두 유한합니다. 반대로 limit을 설정했다고 충분한 용량이 생기는 것도 아닙니다.

이 장의 목표는 다음 순환을 만드는 것입니다.

```text
자원 예산 선언
→ 실제 사용량 측정
→ saturation과 성장률 관찰
→ 제한·backpressure 설정
→ 부하 시험
→ 증설 또는 최적화
→ host·image·dependency 업데이트
→ 회귀와 rollback 검증
```

대응 실습은 [`exercises/16-capacity-and-updates`](../exercises/16-capacity-and-updates/)입니다.

## 1. 자원 budget

호스트 전체 자원을 서비스마다 합계 100%로 나누지 않습니다. kernel, Docker daemon, page cache, 로그 수집과 장애 spike를 위한 여유가 필요합니다.

예:

```text
Host memory 4 GiB
- OS·Docker·관측 700 MiB
- DB steady 1.5 GiB, burst 2.0 GiB
- App steady 500 MiB, burst 900 MiB
- Gateway 100 MiB
- 복구·배포 여유 500 MiB 이상
```

숫자는 측정으로 갱신합니다.

## 2. Memory

limit이 없으면 한 container가 host memory를 고갈시켜 다른 서비스와 daemon까지 영향을 줄 수 있습니다. limit이 너무 낮으면 정상 spike에서 OOM kill이 발생합니다.

확인할 것:

- working set
- cache와 anonymous memory
- OOM kill 횟수
- swap 사용과 latency
- application heap limit
- DB buffer 설정
- 배포 중 old·new container가 겹칠 때 peak

Compose 예:

```yaml
services:
  app:
    mem_limit: 768m
    mem_reservation: 384m
```

사용하는 Compose 구현에서 실제 적용 여부를 `docker inspect`로 확인합니다.

```sh
docker inspect --format '{{.HostConfig.Memory}}' container
```

애플리케이션 runtime이 container limit을 인식하는지도 확인합니다.

## 3. CPU

CPU limit은 noisy neighbor를 제한할 수 있지만 과도한 throttling으로 latency를 높일 수 있습니다.

관찰:

- host load와 runnable process
- container CPU usage
- throttled time
- request latency
- DB query CPU
- encryption·compression backup 작업

평균 CPU가 낮아도 짧은 saturation이 tail latency를 악화시킬 수 있습니다.

## 4. PID와 process

fork bomb, 잘못된 worker 설정이나 zombie 누적으로 PID가 고갈될 수 있습니다.

```yaml
services:
  app:
    pids_limit: 200
```

필요한 worker·subprocess 수를 측정하고 여유를 둡니다. PHP-FPM worker, backup compression과 healthcheck process도 포함합니다.

## 5. File descriptor와 connection

하나의 요청은 client socket, upstream socket, log file과 DB connection을 사용할 수 있습니다.

확인:

```sh
ulimit -n
cat /proc/sys/fs/file-nr
ls /proc/<pid>/fd | wc -l
```

관계:

```text
동시 요청
→ gateway connection
→ app worker
→ DB pool
→ DB max connections
```

application pool의 합이 DB 최대 연결 수보다 크면 작은 spike에도 연결 실패가 발생할 수 있습니다. 관리자·migration·backup용 연결 여유를 남깁니다.

## 6. Disk와 inode

disk 용량만 보지 않습니다.

- database data
- binary log·WAL
- container JSON logs
- image와 build cache
- old release
- backup staging
- upload
- inode 수

성장률로 고갈 시점을 계산합니다.

```text
남은 용량 / 최근 안정된 일평균 증가량 = 대략적인 고갈까지 남은 일수
```

증가가 선형이라는 보장은 없으므로 trend와 spike를 함께 봅니다.

disk가 거의 가득 찬 뒤 정리 자동화를 처음 실행하지 않습니다. 어떤 파일을 지워도 되는지 미리 분류합니다.

## 7. Network와 외부 quota

- ingress·egress bandwidth
- connection tracking table
- DNS query
- registry pull rate
- ACME rate limit
- email·payment API quota
- backup storage request·egress cost

외부 서비스의 제한은 host metric에 보이지 않을 수 있습니다. 응답 header, provider metric과 application error class를 관찰합니다.

## 8. Resource limit과 backpressure

limit은 피해 범위를 제한하지만 요청을 안전하게 처리하는 전략이 필요합니다.

```text
입력률 > 처리률
→ queue 증가
→ memory·latency 증가
→ timeout
→ client retry
→ 더 큰 입력률
```

대응:

- bounded queue
- worker concurrency limit
- request body·upload size limit
- timeout budget
- rate limit
- load shedding
- retry-after
- background job admission control

무제한 queue는 실패를 지연시킬 뿐 제거하지 않습니다.

## 9. 부하 시험

production에 처음 큰 부하를 주지 않습니다. staging 또는 격리 환경에서 대표 workload를 사용합니다.

측정:

- 처리량
- p50·p95·p99 latency
- error rate
- CPU·memory·DB pool
- queue depth
- recovery after load

부하 시험은 최대 숫자 경쟁이 아닙니다. 목표 사용자 부하와 burst에서 SLO를 만족하는지 확인합니다.

데이터 크기와 query 분포가 production과 너무 다르면 결과가 오해를 만들 수 있습니다.

## 10. 용량 변경 결정

다음 중 어느 것이 병목인지 구분합니다.

- CPU
- memory·GC
- DB query·lock
- storage latency
- connection pool
- external dependency
- application serialization
- gateway worker

단순히 호스트 크기를 늘리기 전에 증거를 수집합니다. 그러나 사용자 영향이 진행 중이면 임시 증설로 완화한 뒤 원인을 분석할 수 있습니다.

## 11. 업데이트 대상

```text
Linux package와 kernel
Docker Engine·Compose
base image
application dependency
Nginx·PHP·MariaDB
CI action과 build tool
backup·monitoring agent
```

각 구성요소에 다음을 기록합니다.

- 현재 version
- 지원 종료 시점
- 보안 공지 출처
- 업데이트 주기
- 호환성 검사
- rollback 가능성
- data format 변경 여부

## 12. 재현 가능한 업데이트

Tag만 변경하고 production host에서 즉시 build하지 않습니다.

```text
base·dependency version 변경
→ CI image build
→ test·scan·SBOM
→ staging workload와 restore test
→ 새 digest 생성
→ production 배포
→ 관찰
```

base image digest를 고정했다면 자동 dependency bot 또는 정기 job으로 새 digest 후보를 만듭니다. 고정은 업데이트 책임을 없애지 않습니다.

## 13. Host와 Docker 업데이트

업데이트 전에:

- 최근 backup과 외부 저장 확인
- 현재 release와 rollback image 확인
- 공급자 console 접근 확인
- disk 여유
- 변경 내용과 알려진 호환성
- maintenance window

업데이트 뒤:

- kernel·Docker version
- firewall rule
- Compose network·volume
- systemd unit
- container restart policy
- 외부 TLS·smoke
- log·metric 전송

Docker firewall backend나 기본 동작 변경이 네트워크 경계에 영향을 줄 수 있으므로 외부 포트 검사를 다시 수행합니다.

## 14. Rolling update가 아닌 단일 호스트

단일 replica Compose에서는 process 교체 중 짧은 중단이 생길 수 있습니다. 이를 숨기지 않습니다.

가능한 완화:

- gateway와 app을 분리해 gateway 유지
- application graceful shutdown
- readiness 통과 전 traffic 전달 금지
- 짧은 maintenance 안내
- blue/green을 같은 host에서 임시 운영할 자원 여유

같은 host의 blue/green은 host 장애 고가용성을 제공하지 않으며 배포 전환만 개선합니다. old·new DB schema 호환도 필요합니다.

## 15. 자동 업데이트의 경계

자동으로 적용하기 좋은 변경:

- CI가 검증한 dependency update candidate 생성
- image scan과 SBOM 갱신
- staging 배포
- 비파괴적인 정기 rebuild

사람 승인이나 명시적 maintenance가 필요한 변경:

- kernel 재부팅
- major DB upgrade
- storage format 변경
- Docker network/firewall 동작 변경
- destructive migration
- 복원 절차가 바뀌는 backup 도구 변경

위험 수준과 검증 강도를 연결합니다.

## 16. Capacity review

정기 review에서 다음을 기록합니다.

```text
최근 peak와 steady 사용량
SLO 위반 구간
증가율과 예상 고갈일
resource limit에 근접한 서비스
OOM·restart·throttle
DB connection·storage
registry·backup 보존 사용량
지원 종료 임박 구성요소
다음 변경과 담당자
```

review 문서가 dashboard screenshot만 모으는 보고서가 되지 않도록 결정과 기한을 남깁니다.

## 17. 실습

[`exercises/16-capacity-and-updates`](../exercises/16-capacity-and-updates/)은 30일 host·service metric과 component version 목록을 제공합니다.

학습자는 다음을 계산·판정합니다.

1. memory·disk headroom
2. disk와 backup staging의 고갈 예상일
3. DB pool과 max connection 불일치
4. 반복 OOM·restart와 배포 겹침 위험
5. 지원 종료 또는 오래된 base image 우선순위
6. 증설·제한·최적화 중 선택 근거
7. 업데이트 전·후 검증과 rollback 계획

자동 검사는 숫자 하나뿐 아니라 증거, 임계값, 소유자와 기한이 연결됐는지 확인합니다.

## 18. 공식 확인 자료

- Docker resource constraints: <https://docs.docker.com/engine/containers/resource_constraints/>
- Compose services reference: <https://docs.docker.com/reference/compose-file/services/>
- Docker Engine release notes: <https://docs.docker.com/engine/release-notes/>

다음 장에서는 실제 장애 중 누가 무엇을 어떤 순서로 결정하고 기록하는지 runbook과 사고 대응 흐름을 만듭니다.
