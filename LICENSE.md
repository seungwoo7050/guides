# 라이선스

이 저장소의 문서와 실행 코드는 서로 다른 라이선스를 적용합니다.

## 문서

Markdown 문서와 문서에 포함된 설명, 표와 자체 제작 도식은 [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt)에 따라 이용할 수 있습니다.

문서를 공유하거나 수정해 배포할 때는 저작자 `Seungwoo Kim`과 이 저장소를 적절한 방식으로 표시하고, 변경 여부를 밝혀 주세요.

## 코드

소스 코드, 셸 스크립트, JSON 계약과 실행 가능한 도구는 [MIT License](LICENSES/MIT.txt)에 따라 이용할 수 있습니다.

`exercises/08-renderer-capstone/project/fixtures/`의 scene·marker·invalid/event JSON은 이 저장소가 만든 test input입니다. provenance가 `repository-generated-fixture`, `external_asset: false`, `license: MIT`인 파일과 저장소가 작성한 C++·shader source는 위 MIT 범위에 포함됩니다.

## 외부 자료와 생성물

SDL, SDL_shadercross, RenderDoc, platform SDK, compiler와 외부 명세·도구·asset에는 각 소유자의 라이선스가 우선합니다. 이 저장소는 현재 외부 image·mesh·scene asset이나 생성된 shader binary를 source로 포함하지 않고 [공식 출처](reference/sources.md)와 [고정 version/manifest](reference/version-baseline.md)로 연결합니다.

선택 도구가 만든 `.spv`, `.dxil`, `.msl`, `.metallib`, capture와 build artifact는 자동으로 이 저장소의 MIT 결과물이 되지 않습니다. 재배포 전에는 입력 source, 생성 도구와 runtime의 license·redistribution 조건, 포함된 제3자 자료와 민감 정보를 별도로 확인합니다. 생성물은 기본적으로 `build/` 또는 `out/`에만 두며 tracked source로 commit하지 않습니다.

외부 asset을 추가할 때는 source URL, 가져온 날짜, content hash, 원본 license와 재배포 가능 여부, import 변환을 함께 기록해야 합니다. 실행·capture·생성물의 운영 제약은 [안전 및 운영 계약](SAFETY.md)을 따릅니다.
