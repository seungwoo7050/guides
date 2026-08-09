# 구현·리뷰 체크리스트

수식 정본은 [수학 규약과 공식](../docs/90-appendix/01-math-conventions-and-formulas.md)을 사용합니다.

## 좌표

- [ ] vector가 position/direction/normal 중 무엇인지 드러나는가?
- [ ] local/world/view/clip/NDC/viewport 공간이 이름에 있는가?
- [ ] `P * V * M * p`와 column-vector 규약이 일관적인가?
- [ ] clipping 전에 `w`를 보존하는가?
- [ ] viewport Y와 front-face가 한 번만 변환되는가?
- [ ] 비균일 scale에서 normal matrix를 쓰는가?

## rasterization

- [ ] pixel center가 `(x+0.5,y+0.5)`인가?
- [ ] bounding box rounding이 sample convention과 맞는가?
- [ ] top-left rule이 shared edge를 한 번만 소유하는가?
- [ ] degenerate·culled·clipped 통계가 분리되는가?
- [ ] flat/affine/perspective attribute가 구분되는가?
- [ ] depth convention, clear, compare와 write가 일치하는가?

## color·texture

- [ ] texture가 color인지 data인지 구분되는가?
- [ ] filtering·mipmap·lighting·blend가 linear인가?
- [ ] sRGB decode/encode 위치가 명시되는가?
- [ ] straight/premultiplied alpha와 blend factor가 일치하는가?
- [ ] UV origin, address와 texel center fixture가 있는가?
- [ ] normal map이 sRGB로 처리되지 않는가?

## asset

- [ ] attribute count와 index range를 검사하는가?
- [ ] NaN/inf와 invalid transform을 거부하는가?
- [ ] hierarchy cycle과 stale handle을 검출하는가?
- [ ] bounds가 geometry를 보수적으로 포함하는가?
- [ ] axis/unit/color/normal convention을 입구에서 정규화하는가?
- [ ] source/import profile/content hash를 기록하는가?

## GPU

- [ ] resource descriptor의 usage와 실제 pass 사용이 맞는가?
- [ ] C++ layout과 shader offset/format을 검증하는가?
- [ ] shader compiler·target·binding manifest가 있는가?
- [ ] pipeline key가 모든 고정 state와 attachment format을 포함하는가?
- [ ] frame slot 재사용이 completion에 연결되는가?
- [ ] reload/resize resource를 last-use 완료 뒤 파괴하는가?
- [ ] zero extent와 acquire 실패를 분류하는가?

## debug·성능

- [ ] frame/pass/resource/draw에 일관된 label이 있는가?
- [ ] validation baseline과 새 warning 정책이 있는가?
- [ ] 최종 image 전에 coverage·depth·attribute artifact가 있는가?
- [ ] CPU와 GPU timing을 다른 방식으로 측정하는가?
- [ ] median/p95와 workload/environment를 기록하는가?
- [ ] 최적화 전후 correctness hash와 memory/complexity 비용이 있는가?

## 공개 전

- [ ] `./prepare.sh && ./verify.sh`가 통과하는가?
- [ ] 내부 링크와 실습 계약 참조가 유효한가?
- [ ] 알려진 오답 mutation이 검사기에 거부되는가?
- [ ] reference image 변경 이유와 diff가 있는가?
- [ ] 외부 asset·shader·도구의 라이선스를 확인했는가?
- [ ] 구현하지 않은 범위와 지원 환경을 숨기지 않는가?
