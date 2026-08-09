# 검토된 reference artifact

작은 결정적 CPU 결과와 GPU 비교 전에 선언한 edge 정책만 추적합니다. [`manifest.json`](manifest.json)은 각 기준 파일의 SHA-256·MIT provenance와 변경 정책을 고정하고, [`gpu-edge-policy.json`](gpu-edge-policy.json)은 64×64 공통 scene의 mask hash·최대 비율·허용 수치를 GPU readback보다 먼저 선언합니다.

backend별 GPU 출력은 추적 정답으로 덮어쓰지 않습니다. PPM·trace·edge 정책을 바꿀 때는 첫 달라진 pipeline 단계, 수치 근거와 known-bad 회귀 결과를 함께 검토합니다. 실패한 뒤 mask나 tolerance를 넓혀 통과시키지 않습니다.
