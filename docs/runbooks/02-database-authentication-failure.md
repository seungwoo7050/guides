# Runbook: 데이터베이스 인증 실패

## 대상 증상과 사용자 영향

- 애플리케이션 로그에 access denied, authentication failed 또는 credential 오류가 나타납니다.
- DB container는 정상이어도 읽기·쓰기 경로가 실패할 수 있습니다.
- Secret 회전 직후 일부 worker만 실패할 수 있습니다.

## 필요한 권한과 도구

- 애플리케이션·DB 상태와 로그 읽기 권한
- Secret **metadata와 version** 읽기 권한
- DB 사용자·권한을 확인할 승인된 관리자 경로
- Secret 원본을 회전할 권한은 진단 권한과 분리하는 것이 좋습니다.

## 사전 안전 조건

- Secret 값을 로그, terminal 공유 화면, 사고 문서에 출력하지 않습니다.
- 실패했다고 DB 사용자나 데이터를 먼저 삭제하지 않습니다.
- 현재와 이전 credential의 유효 기간과 소비자 목록을 확인합니다.

## 1. 실패 범위 확인

- 모든 instance가 실패하는가?
- 새 connection만 실패하는가, 기존 connection은 유지되는가?
- 특정 DB 사용자·database만 실패하는가?
- Secret 회전 또는 deployment 직후 시작됐는가?

```sh
cd /srv/example
docker compose ps -a
docker compose logs --since 15m --no-color app db
```

실제 비밀번호가 포함된 오류 문장은 외부 사고 채널로 복사하지 않습니다.

## 2. DB 자체 준비 상태 분리

DB의 로컬 protocol health가 실패하면 인증보다 DB lifecycle·disk·recovery 문제를 먼저 조사합니다.

```sh
docker compose ps db
docker compose logs --since 15m --no-color db
```

확인:

- DB process가 실행 중인가?
- recovery·upgrade·disk full 상태인가?
- 기대 database와 사용자가 존재하는가?
- 계정이 잠겼거나 만료됐는가?

## 3. Secret 경로와 version 확인

값을 읽어 화면에 표시하지 않고 다음 metadata만 확인합니다.

```sh
stat /etc/example/secrets/db_password_v2
readlink /etc/example/secrets/db_password_current 2>/dev/null || true
```

확인:

- Compose가 기대 secret 이름을 mount하는가?
- Host 파일 owner·group·mode가 맞는가?
- Container 내부 경로가 설정과 같은가?
- 현재 pointer와 release manifest의 required secret version이 같은가?
- 파일 끝 newline이나 encoding을 소비자가 어떻게 처리하는가?

## 4. 승인된 방식으로 credential 검증

비밀번호를 command-line argument로 넘기지 않습니다. DB client가 보호된 option file, stdin 또는 secret file을 지원하면 그 경로를 사용합니다.

검증은 최소 권한의 읽기 전용 질의로 제한합니다.

```text
연결 성공
→ 현재 사용자 확인
→ 대상 database 접근
→ SELECT 1 또는 읽기 전용 query
```

관리자 credential로 성공했다는 사실은 애플리케이션 credential이 정상이라는 뜻이 아닙니다.

## 5. 회전 상태 분기

### 새 credential이 DB에 등록되지 않음

- 새 값을 candidate로 유지합니다.
- 현재 pointer를 바꾸지 않습니다.
- DB에 새 credential을 등록하고 별도 connection으로 검증합니다.

### DB는 새 credential을 허용하지만 app가 옛 값을 사용

- Container mount와 process reload 경계를 확인합니다.
- Connection pool이 기존 connection을 계속 유지하는지 봅니다.
- 안전한 rolling restart 또는 connection 재생성을 수행합니다.

### 일부 worker만 실패

- 모든 replica의 release와 secret version을 비교합니다.
- 같은 service 안에 old·new container가 섞였는지 확인합니다.

### 이전 credential을 너무 일찍 폐기

- 감사 기록으로 누가 언제 폐기했는지 확인합니다.
- 새 credential이 모든 소비자에서 동작하면 앞으로 진행합니다.
- 새 credential도 실패하면 데이터·보안 소유자 승인 아래 제한적으로 이전 credential 복구 또는 새 값 재발급을 결정합니다.

## 6. 가역 완화

- 검증된 현재 credential pointer로 되돌립니다.
- 실패한 새 release가 다른 secret schema를 요구하면 호환 이전 release로 rollback합니다.
- 쓰기 경로를 일시 중지하고 읽기만 유지합니다.

실패한 credential을 로그에 남기는 debug 설정은 사용하지 않습니다.

## 7. 복구 확인

- 새 DB connection이 성공합니다.
- 핵심 읽기·쓰기와 transaction이 성공합니다.
- 모든 worker가 같은 secret version을 사용합니다.
- 폐기한 옛 credential은 실제로 거부됩니다.
- 로그와 metric에 secret 값이 없습니다.
- DB authentication error rate가 정상화됩니다.

## 8. 증거와 후속 작업

```text
실패한 secret 이름·version, 값 제외
영향받은 release와 instance
DB 사용자 상태
회전 timeline
Pointer 전환·rollback 결과
옛 credential 폐기 확인
재현 가능한 rotation test
```
