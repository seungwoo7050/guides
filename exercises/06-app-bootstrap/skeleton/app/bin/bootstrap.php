<?php
declare(strict_types=1);

// TODO:
// - 환경변수와 비밀값 파일에서 데이터베이스 접속 정보를 읽습니다.
// - 제한된 횟수만 재시도하며 PDO로 접속합니다.
// - app_meta와 notes 테이블을 IF NOT EXISTS로 만듭니다.
// - seed_v1 표시를 INSERT IGNORE한 최초 한 번에만 초기 메모를 추가합니다.

fwrite(STDERR, "TODO: implement idempotent bootstrap\n");
exit(1);
