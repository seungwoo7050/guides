# Unix 시스템 관찰과 진단 가이드

Unix 사용자 공간에서 경로·파일 디스크립터·프로세스·권한·메모리·네트워크 엔드포인트·서비스 상태를 관찰하고, 증상을 근거로 실패 계층을 좁히는 가이드입니다.

이 저장소는 C로 POSIX 기능을 다시 구현하는 과정이 아닙니다. 터미널 화면에 나타난 결과를 다음 상태 모델과 연결하는 데 집중합니다.

```text
입력과 실행 문맥
→ 경로와 자원
→ 프로세스와 수명
→ 메모리와 네트워크 상태
→ 서비스 준비 상태
→ 가설·반증·복구 검증
```

## 시작

Overlay를 적용한 저장소 루트에서 다음 순서로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

- `prepare.sh`: source tree와 Git index를 변경하지 않는 구조·도구·fingerprint 확인
- `verify.sh`: 최종 구조, 문서 링크, 답안 검사기와 아홉 개의 재현 시나리오 전체 검사

학습 경로와 범위는 [문서 로드맵](docs/00-roadmap.md)에서 확인합니다.

## 문서 구성

### 1부: 사용자 공간의 객체와 경계

1. [터미널, 프로세스와 커널](docs/01-user-space-model/01-terminal-process-and-kernel.md)
2. [파일, 경로와 메타데이터](docs/01-user-space-model/02-files-paths-and-metadata.md)
3. [스트림, 파일 디스크립터와 파이프](docs/01-user-space-model/03-streams-file-descriptors-and-pipes.md)
4. [사용자, 권한과 환경](docs/01-user-space-model/04-users-permissions-and-environment.md)

### 2부: 프로세스와 자원 관찰

5. [프로세스, 시그널과 작업 제어](docs/02-process-and-resource-observation/01-processes-signals-and-jobs.md)
6. [프로세스 메모리 관찰](docs/02-process-and-resource-observation/02-process-memory-observation.md)
7. [네트워크 엔드포인트와 연결 진단](docs/02-process-and-resource-observation/03-network-endpoints-and-diagnosis.md)

### 3부: 서비스와 문제 해결

8. [서비스 감독, 로그와 준비 상태](docs/03-services-and-troubleshooting/01-service-supervision-logs-and-readiness.md)
9. [시스템 문제 진단](docs/03-services-and-troubleshooting/02-system-troubleshooting.md)

## 누적 실습

[시스템 조사 실습](exercises/system-investigation/README.md)은 다음 아홉 상황을 현재 사용자 권한과 loopback 안에서 재현합니다.

```text
명령 탐색 우선순위
끊어진 심볼릭 링크
입력을 기다리는 프로세스
삭제됐지만 열린 파일
잘못된 작업 디렉터리
IPv4/IPv6 주소 계열 불일치
실행 중이지만 준비되지 않은 서비스
전달되지 않은 종료 시그널
예약됐지만 상주하지 않은 메모리
```

```sh
cd exercises/system-investigation
./create-workspace.sh
python3 lab.py list
python3 lab.py create 01-command-resolution workspace/case-01
python3 lab.py symptom workspace/case-01
```

조사가 끝난 사례는 반드시 정리합니다.

```sh
python3 lab.py destroy workspace/case-01
```

## 안전 범위

- 관리자 권한을 요구하지 않습니다.
- 외부 주소를 사용하거나 scan하지 않습니다.
- 외부 Python package를 설치하지 않습니다.
- 사례는 지정한 작업 디렉터리와 loopback만 사용합니다.
- 사용자 `workspace/`는 준비·검증 과정에서 자동 삭제하지 않습니다.
- `sudo`, 광범위한 재귀 삭제, `chmod 777`, 첫 대응으로 사용하는 `kill -9`를 해결책으로 제시하지 않습니다.

macOS와 Linux는 같은 목적의 관찰 도구가 다를 수 있습니다. 출력 형식을 외우기보다 각 명령이 어떤 상태를 증명하는지 확인합니다.
