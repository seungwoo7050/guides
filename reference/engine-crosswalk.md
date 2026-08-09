# 엔진 개념 교차표

이 표는 API 대응표가 아니라 문서의 질문을 엔진 프로젝트에서 어디부터 조사할지 알려 주는 시작점이다. 정확한 class와 수명은 사용하는 엔진 버전·framework와 프로젝트 코드를 확인한다.

| 이 가이드의 개념 | Unreal 계열에서 조사할 곳 | Unity 계열에서 조사할 곳 | Godot 계열에서 조사할 곳 | 확인 질문 |
|---|---|---|---|---|
| process/game instance scope | Engine/GameInstance/subsystem | bootstrap object, persistent service, player loop | autoload/main loop | 누가 만들고 shutdown 순서는 무엇인가? |
| world/scene scope | World, level/streaming, world subsystem | Scene, additive loading, scene-bound object | SceneTree, scene/node | load cancel과 unload 뒤 무엇이 남는가? |
| match/rule authority | GameMode/GameState 또는 project rule system | project simulation/rule service | project authority node/service | rule result의 최종 writer는 누구인가? |
| entity/component | Actor/Pawn/Component | GameObject/Component 또는 ECS entity | Node/Resource/project entity | identity와 runtime lifetime은 무엇인가? |
| fixed simulation | fixed tick/physics or custom simulation | FixedUpdate/player loop/custom tick | physics process/custom tick | render frame과 command consumption이 분리되는가? |
| input action | Enhanced Input/action mapping | Input System action map | InputMap/action event | device binding과 command가 분리되는가? |
| asset identity/loading | Asset Manager, soft reference, async load | GUID/addressable/project asset pipeline | Resource path/UID/loader | persistent id와 runtime handle이 다른가? |
| save/replay | project SaveGame/replay/network demo | project serialization/replay | project resource/file serialization | schema와 content/build version이 있는가? |
| networking | replication/RPC/ownership model | package/project networking stack | MultiplayerAPI/peer/project protocol | client가 intent만 제출하는가? |
| profiling | Insights/stat/target capture | Profiler/target capture | profiler/monitor/custom trace | 실제 target·workload·build인가? |

## 사용 방법

1. 먼저 가이드 용어로 owner, state, lifetime과 failure를 작성한다.
2. 엔진 문서에서 비슷한 이름을 찾는다.
3. 실제 프로젝트 코드에서 wrapper, framework와 custom subsystem을 확인한다.
4. 이름이 같다는 이유로 보장이 같다고 가정하지 않는다.
5. lifecycle trace와 작은 failure fixture로 매핑을 검증한다.

공식 문서 링크와 확인 날짜는 [엔진 교차표와 공식 자료 지도](../docs/90-engine-and-source-map.md)를 사용한다.
