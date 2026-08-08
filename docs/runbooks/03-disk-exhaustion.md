# Runbook: Disk·inode 고갈

## 대상 증상과 사용자 영향

- 쓰기 실패, DB 중단, image pull 실패, log 기록 실패가 발생합니다.
- `No space left on device`는 byte 부족뿐 아니라 inode 부족일 수 있습니다.
- Disk 사용률이 높아도 무엇을 삭제해도 되는지는 별도 판단입니다.

## 사전 안전 조건

- DB data, upload, 현재·rollback image와 유일한 backup을 삭제하지 않습니다.
- 자동 `docker system prune -a`, `down -v`, 광범위한 `rm -rf`를 실행하지 않습니다.
- 먼저 filesystem과 증가 원인을 확인합니다.

## 1. Byte와 inode 확인

```sh
df -h
df -i
findmnt
lsblk -f
```

기록:

- 어떤 mount가 고갈됐는가?
- byte인가 inode인가?
- read-only remount나 I/O error가 있는가?
- 증가 속도는 얼마인가?

## 2. 큰 범주 찾기

Filesystem 경계를 넘지 않도록 `-x`를 사용합니다.

```sh
sudo du -x -h -d 1 /var 2>/dev/null | sort -h
sudo du -x -h -d 1 /srv 2>/dev/null | sort -h
docker system df
journalctl --disk-usage
```

Deleted-open file도 확인합니다.

```sh
sudo lsof +L1 2>/dev/null || true
```

파일을 삭제했는데 공간이 돌아오지 않으면 process가 열린 descriptor를 유지할 수 있습니다.

## 3. 원인 분류

### Container log 증가

- logging driver와 rotation 설정을 확인합니다.
- 특정 release의 반복 오류가 log storm을 만드는지 봅니다.
- 알려진 log만 rotate하고 process가 reopen하는지 확인합니다.

### Image·build cache 증가

- 현재와 rollback release가 참조하는 digest를 먼저 목록화합니다.
- 미참조 cache와 중간 image만 선택적으로 정리합니다.
- Production host에서 build하지 않으면 build cache가 커지는 원인을 조사합니다.

### DB data·WAL·binary log 증가

- DB별 안전한 보존·purge 명령을 사용합니다.
- replica·backup·point-in-time recovery가 필요한 log를 임의 삭제하지 않습니다.
- 비정상 transaction, vacuum·checkpoint 또는 retention 실패를 조사합니다.

### Backup staging 증가

- 외부 upload와 checksum 검증이 완료된 artifact만 staging에서 제거합니다.
- 마지막 성공 backup과 유일한 복사본을 삭제하지 않습니다.

### Upload·업무 데이터 증가

- 사용자 데이터 보존 정책과 application 삭제 경로를 따릅니다.
- Shell에서 임의 삭제하지 않습니다.

### inode 고갈

- 작은 파일이 대량 생성되는 cache, session, temporary directory를 찾습니다.
- 생성 주체와 lifecycle을 수정합니다.

## 4. 가역 완화

우선순위 예:

1. 비필수 쓰기·batch job 중지
2. 알려진 temporary file 생성 중지
3. 보존 정책이 명확한 old log rotate·압축
4. 검증 완료 backup staging을 외부 확인 후 제거
5. 참조되지 않는 build cache 선택 정리
6. Disk 확장 또는 새 volume 부착

DB가 이미 read-only 또는 crash 상태라면 반복 재시작보다 공간을 확보하고 DB 복구 절차를 따릅니다.

## 5. 고위험 조치 승인 경계

다음은 resource ID, 예상 회수량, backup과 rollback 영향을 출력한 dry-run 뒤 승인합니다.

- Docker image 일괄 삭제
- DB log purge
- Upload 삭제
- Filesystem resize
- Volume 이동
- Retention 정책 변경

## 6. 복구 확인

- Byte와 inode에 운영 여유가 생겼습니다.
- DB와 application 쓰기가 성공합니다.
- Restart loop가 멈췄습니다.
- Log·backup·upload 증가율이 정상화됩니다.
- Disk forecast와 alert가 갱신됩니다.
- 같은 원인이 다시 증가할 때 경보가 충분히 일찍 울립니다.

## 7. 증거와 후속 작업

```text
고갈 mount와 시각
Byte·inode 전후 값
상위 증가 경로
삭제·이동한 resource ID
보호한 current·rollback·backup 목록
원인 release·job
새 limit·rotation·retention
고갈 예상일까지 남은 시간
```
