# Relay Arena runtime brief

- `GameProcess`는 boot부터 process 종료까지 존재한다.
- `FrontEndWorld`와 `ArenaWorld`는 동시에 resident할 수 있지만 active world는 하나다.
- `ArenaSession`은 arena load 요청부터 결과 commit 또는 cancel까지 존재한다.
- `MatchState`는 loading이 끝난 뒤 생성되고 restart마다 generation이 증가한다.
- `PlayerEntity`, 세 개의 `RelayCore`, `HazardSpawner`는 match-owned다.
- `AudioDirector`와 `TelemetryClient`는 process-owned다.
- `ArenaHud`는 active local player와 match를 projection한다.
- navmesh와 cosmetic bundle은 비동기 loading된다.
- persistent progression은 result commit 성공 뒤에만 갱신된다.
