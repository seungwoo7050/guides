# Backup과 별도 대상 복원

합성 database dump와 upload를 일관된 backup artifact로 만들고, 빈 대상에 복원한 뒤 사용자 수준 계약을 검사합니다.

관련 문서: [`docs/15-backup-restore-and-disaster-recovery.md`](../../docs/15-backup-restore-and-disaster-recovery.md)

## 구현 계약

`skeleton/backup.py`의 두 함수를 완성합니다.

```python
create_backup(source, destination, backup_id, created_at)
restore_backup(backup_directory, target)
```

### Backup

- source를 수정하지 않음
- staging 디렉터리에서 artifact 완성
- database와 upload archive의 size·SHA-256 기록
- source release·schema·최신 record 시각 기록
- 완성된 directory를 원자적으로 공개
- 그 뒤에만 `CURRENT` pointer 갱신

### Restore

- checksum이 틀리면 복원 중단
- 비어 있지 않은 대상에 기본 덮어쓰기 금지
- archive path traversal 거부
- DB가 참조하는 모든 upload와 checksum 확인
- 사용자 읽기·쓰기 smoke가 가능한 구조로 복원

## 검증

```sh
cd exercises/15-disaster-recovery
./verify.sh skeleton
./verify.sh reference
```

검증기는 다음을 확인합니다.

- 정상 backup과 복원, manifest, size·SHA-256, `CURRENT` pointer
- 손상 artifact와 비어 있지 않은 대상 거부
- `../` 경로 탈출 archive가 대상 밖에 파일을 만들지 못함
- symlink나 특수 파일이 섞인 source 거부
- 실패한 복원이 부분 결과를 공개하지 않음
- source snapshot을 변경하지 않음
