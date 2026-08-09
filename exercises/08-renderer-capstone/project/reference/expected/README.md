# 검토된 reference artifact

작은 결정적 CPU 결과만 추적합니다. GPU 출력은 이 디렉터리의 CPU artifact·manifest와 실행 시 비교하며 backend별 결과를 정답으로 덮어쓰지 않습니다. PPM/PGM을 바꿀 때는 첫 달라진 pipeline 단계와 known-bad 회귀 결과를 함께 검토합니다.
