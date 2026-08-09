# 게임 개발 용어

이 용어집은 엔진마다 다른 이름을 하나로 강제하지 않는다. 문서에서 사용하는 의미와 서로 구분해야 하는 경계를 고정한다.

## action

물리 장치의 key/button/axis를 게임이나 UI가 이해하는 논리적 입력으로 바꾼 결과다. `Dash`, `Confirm`, `Navigate`가 예다. device binding과 분리한다.

## command

특정 player가 특정 tick/sequence에 simulation에 제출하는 의도다. 결과가 아니라 `move`, `dash`, `interact` 같은 요청을 표현한다.

## authoritative state

최종 결과를 결정할 권한이 있는 정본 상태다. local game에서는 rule simulation, multiplayer에서는 보통 server/host가 writer다. UI, animation, prediction과 telemetry는 별도 view일 수 있다.

## presentation state

animation, audio, VFX, camera, UI처럼 authoritative game event/state를 사용자에게 표현하기 위한 상태다. 특별한 설계가 없는 한 gameplay 결과의 정본이 아니다.

## render frame

화면을 제출·표시하기 위한 한 번의 rendering 주기다. simulation tick과 같지 않으며 한 frame에 simulation step이 0개, 1개 또는 여러 개일 수 있다.

## fixed simulation tick

정해진 시간 간격으로 gameplay/physics 규칙을 진행하는 integer step이다. replay, command ordering과 authoritative timeline에 사용하기 쉽다.

## game time

pause, slow motion과 gameplay policy의 영향을 받는 시간축이다. network timeout이나 실제 duration 측정에 그대로 사용하지 않는다.

## world / scene / level

게임 객체가 존재하고 update되는 runtime 공간 또는 콘텐츠 구획이다. 엔진마다 구조가 다르므로 반드시 owner, activation, unload와 generation을 함께 정의한다.

## entity

게임 세계에서 식별 가능한 runtime 대상이다. persistent stable id, runtime instance id와 network id는 같은 값일 필요가 없다.

## component

entity 또는 object의 한 책임과 데이터를 제공하는 구성 요소다. 무조건적인 ECS 의미로만 사용하지 않는다.

## subsystem / service

world, game instance, process 등 특정 수명을 가진 공통 기능 owner다. global singleton이라는 뜻이 아니다.

## stable id

save, content, replay와 network가 runtime 주소 대신 사용하는 의미 기반 식별자다. rename/removal 때 migration 또는 alias 정책이 필요하다.

## runtime handle

현재 process/generation에서 살아 있는 object/resource를 가리키는 참조다. stable id와 달리 unload/restart 뒤 무효가 될 수 있다.

## generation

같은 논리적 종류의 world/match/request가 다시 만들어졌음을 구분하는 증가 식별자다. 이전 generation의 callback/snapshot을 거부하는 데 사용한다.

## asset

source file만을 뜻하지 않는다. logical asset id, imported artifact, cooked package와 runtime resource를 문맥에 따라 구분한다.

## cooking / build processing

source content를 target platform이 읽을 수 있는 변환·압축·패키지 형태로 만드는 과정이다. 엔진마다 import, cook, bake, build 등의 이름을 사용한다.

## control-ready

player가 gameplay를 안전하게 시작할 수 있는 critical state/content가 준비된 시점이다. cosmetic-ready와 분리할 수 있다.

## resident

runtime resource가 CPU/GPU/audio memory 등 사용 가능한 메모리에 실제로 남아 있는 상태다. 파일이 package에 들어 있다는 뜻과 다르다.

## gameplay event

authoritative state transition이 발생했음을 표현하는 의미 event다. presentation one-shot과 telemetry event는 이를 서로 다른 목적으로 투영할 수 있다.

## save

나중에 플레이를 계속하기 위한 durable semantic state다. raw runtime object memory나 presentation cache를 그대로 보존하는 기능이 아니다.

## replay

initial state와 ordered command/event를 적용해 gameplay 결과 또는 조사 가능한 경험을 재구성하는 기록이다. save와 목적·필드가 다르다.

## determinism

정한 platform/build/content/input 범위에서 같은 state transition 또는 hash를 재현하는 성질이다. 범위를 쓰지 않은 “완전 결정적”이라는 표현은 사용하지 않는다.

## prediction

authoritative result를 기다리는 동안 local client가 player experience를 위해 결과를 임시 계산하는 방식이다. prediction은 authority 이전이 아니다.

## correction / reconciliation

authoritative snapshot/result와 local prediction 차이를 반영하는 과정이다. simulation state, camera와 presentation one-shot을 서로 다른 정책으로 처리할 수 있다.

## rollback

과거 tick/snapshot으로 state를 되돌리고 command를 다시 적용하는 방식 또는 release artifact를 이전 상태로 복구하는 작업이다. 두 의미는 문맥에 따라 구분한다.

## frame budget

한 frame을 target refresh 안에 완료하기 위해 허용한 critical-path 시간과 subsystem 제약이다. CPU와 GPU 시간의 단순 합이 아니다.

## hitch

steady frame보다 현저히 긴 단일 또는 짧은 연속 frame이다. 평균 FPS가 좋아도 input, animation과 simulation에 큰 영향을 줄 수 있다.

## vertical slice

입력부터 gameplay, presentation, content, save/network, 품질과 release까지 하나의 얇은 사용자 경로를 끝까지 연결한 결과물이다. 많은 콘텐츠를 뜻하지 않는다.
