# 엔진 교차표와 공식 자료 지도

이 문서는 엔진별 튜토리얼을 대신하지 않습니다. 가이드에서 사용하는 개념을 Unity, Unreal Engine과 Godot의 공식 용어에 연결해 낯선 코드베이스의 문서를 찾는 출발점으로 사용합니다.

공식 문서의 API, package와 권장 방식은 바뀔 수 있습니다. 아래 자료는 **2026-08-09에 확인한 진입 링크**이며, 프로젝트가 사용하는 정확한 engine version의 문서를 다시 확인해야 합니다.

확인 범위는 아래 21개 URL이 Epic, Unity, Godot, Microsoft와 Steamworks의 공식 domain에서 의도한 문서로 열리는지와 제목·주제가 설명에 맞는지까지입니다. 현재 Epic 링크는 Unreal Engine 5.8 문서로, Godot 링크는 rolling `stable` 문서로 해석되므로 이 확인이 개별 프로젝트 version과 API compatibility를 보장하지는 않습니다. 네트워크 확인은 로컬 `verify.sh`의 필수 조건이 아니며 링크가 바뀌면 확인일과 설명을 함께 갱신합니다.

## 개념 교차표

| 가이드 개념 | Unity 계열 | Unreal Engine 계열 | Godot 계열 |
|---|---|---|---|
| runtime world/scene | Scene, GameObject, Component | World, Level, Actor, Actor Component | SceneTree, Node, PackedScene |
| process-level state | persistent object/service, bootstrap scene | GameInstance, subsystem | autoload, root node/service |
| match rule/public state | project-specific systems | GameMode, GameState, PlayerState | project-specific nodes/resources/multiplayer authority |
| variable update | `Update` | Actor/Component tick | `_process` |
| fixed simulation | `FixedUpdate`, fixed timestep | physics tick/substepping/project systems | `_physics_process` |
| authored data | ScriptableObject, prefab | Data Asset, Blueprint/Data-only asset | Resource, scene |
| asset discovery/loading | Addressables/AssetBundle and project pipeline | Asset Registry, Asset Manager, cooking/chunking | ResourceLoader, import/export pipeline |
| input action | Input System action/binding | Enhanced Input action/mapping context | InputMap/action |
| profiling | Unity Profiler, target-device capture | Unreal Insights, stat/profile tools | debugger/profiler/monitor tools |
| multiplayer | Netcode/project networking | replication, RPC, GameState/PlayerState | MultiplayerAPI, high-level multiplayer |
| build content | Build Profiles, player build/content pipeline | cook, package, stage, chunk | export preset/template |

이 표는 이름 대응일 뿐 동일한 수명과 보장을 뜻하지 않습니다. 실제 프로젝트의 callback order, ownership, thread와 network authority를 확인합니다.

## 공식 자료

### Unreal Engine

- [Gameplay Framework](https://dev.epicgames.com/documentation/en-us/unreal-engine/gameplay-framework-in-unreal-engine): GameInstance, GameMode, GameState, PlayerState, Controller, Pawn과 World의 역할을 확인합니다.
- [Game Mode and Game State](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-mode-and-game-state-in-unreal-engine): server-only rule owner와 replicated public match state의 구분을 확인합니다.
- [Game Framework Component Manager](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-framework-component-manager-in-unreal-engine): network와 dependency가 있는 actor initialization state 사례를 확인합니다.
- [Asset Management](https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-management-in-unreal-engine): Primary/Secondary Asset, Asset Manager, async loading, cooking/chunking과 audit 경계를 확인합니다.
- [Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine): replication, sessions, replay와 network debugging의 진입점입니다.
- [Actor Owner and Owning Connection](https://dev.epicgames.com/documentation/en-us/unreal-engine/actor-owner-and-owning-connection-in-unreal-engine): owner, owning connection과 RPC/replication authority의 관계를 확인합니다.
- [Testing and Debugging Networked Games](https://dev.epicgames.com/documentation/en-us/unreal-engine/testing-and-debugging-networked-games-in-unreal-engine): multi-instance test와 network profiling 도구의 범위를 확인합니다.

### Unity

- [Time](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Time.html): `deltaTime`, `fixedDeltaTime`, frame와 fixed update의 기본 API를 확인합니다.
- [Fixed updates](https://docs.unity3d.com/6000.0/Documentation/Manual/fixed-updates.html): fixed simulation 주기와 frame 사이 관계를 확인합니다.
- [Input](https://docs.unity3d.com/6000.0/Documentation/Manual/Input.html): device input과 현재 권장 Input System의 진입점입니다.
- [Input System package](https://docs.unity3d.com/6000.0/Documentation/Manual/com.unity.inputsystem.html): action, binding과 device abstraction을 확인합니다.
- [Collect performance data on a target platform](https://docs.unity3d.com/6000.0/Documentation/Manual/profiling-target-device.html): editor가 아니라 target build를 profile하는 절차를 확인합니다.
- [Memory Profiler](https://docs.unity3d.com/6000.0/Documentation/Manual/com.unity.memoryprofiler.html): object·allocation·snapshot 기반 memory 조사 도구를 확인합니다.

### Godot

- [SceneTree](https://docs.godotengine.org/en/stable/classes/class_scenetree.html): scene hierarchy, lifecycle와 main loop 접점을 확인합니다.
- [Nodes and scene instances](https://docs.godotengine.org/en/stable/tutorials/scripting/nodes_and_scene_instances.html): Node와 reusable scene composition의 진입점입니다.
- [Resources](https://docs.godotengine.org/en/stable/tutorials/scripting/resources.html): data와 resource loading/caching의 개념을 확인합니다.
- [High-level multiplayer](https://docs.godotengine.org/en/stable/tutorials/networking/high_level_multiplayer.html): SceneTree/MultiplayerAPI와 peer 구성의 진입점입니다.
- [The main game loop](https://docs.godotengine.org/en/stable/tutorials/scripting/idle_and_physics_processing.html): frame processing과 physics processing의 구분을 확인합니다.

### Platform·접근성·배포

- [Xbox Accessibility Guidelines](https://learn.microsoft.com/en-us/xbox/accessibility/guidelines): input, text, audio, visual, timing과 UI의 접근성 검토 출발점입니다.
- [Gaming and Disability Player Experience Guide](https://learn.microsoft.com/en-us/xbox/accessibility/gadpeg): 기능 목록보다 player가 만나는 장벽 관점으로 검토합니다.
- [Steamworks Builds](https://partner.steamgames.com/doc/store/application/builds): build, depot와 manifest의 배포 단위를 확인합니다.

## 자료를 읽는 순서

1. 현재 project engine version을 확인합니다.
2. project의 bootstrap, world/scene, player와 rules class를 찾습니다.
3. official lifecycle 문서와 실제 project trace를 비교합니다.
4. asset/build/network/profile 도구가 어떤 상태를 보장하는지 확인합니다.
5. engine 문서가 보장하지 않는 project-specific invariant를 별도 문서와 test로 고정합니다.

## 엔진 선택 기준

학습용 첫 engine을 “가장 좋은 엔진”으로 고르지 않습니다. 목표와 constraint를 기준으로 선택합니다.

- 참여하려는 회사와 open-source project가 사용하는가
- target platform을 지원하는가
- source와 debugging access가 필요한가
- team의 art/content workflow에 맞는가
- networking, build와 profiling 요구를 충족하는가
- license와 distribution 조건을 검토했는가

한 engine에서 만든 vertical slice를 완료한 뒤 다른 engine으로 옮길 때 이 가이드의 state·lifetime·failure·evidence 항목을 crosswalk로 사용합니다.
