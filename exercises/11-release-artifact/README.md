# 변경 불가능한 release 산출물

작은 애플리케이션 Dockerfile과 release manifest를 운영 배포 단위로 완성합니다.

관련 문서: [`docs/11-image-registry-and-release-artifacts.md`](../../docs/11-image-registry-and-release-artifacts.md)

## 구현 대상

```text
skeleton/Dockerfile
skeleton/release.yaml
```

Dockerfile은 다음을 만족해야 합니다.

- 명시적인 base image version
- 비root runtime 사용자
- exec 형식 entrypoint
- source revision·version·created OCI label
- build 또는 runtime secret을 image에 저장하지 않음

release manifest는 다음을 만족해야 합니다.

- exact image digest
- source revision과 release ID
- schema·configuration 호환 범위
- 필요한 secret의 이름만 기록
- SBOM과 provenance의 subject가 배포 digest와 일치
- 이전 exact digest rollback 대상
- registry pull 권한과 보존 기간

## 검증

```sh
cd exercises/11-release-artifact
./verify.sh skeleton
./verify.sh reference
```

실습 digest는 형식 검사용 합성 값입니다. 실제 운영에서는 registry push 결과로 얻은 digest와 attestation을 사용합니다.
