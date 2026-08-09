# 입력과 명령 계약 제출

## 식별자와 소유권

| 식별자 | 의미 | owner | lifetime | 다른 id와 같지 않은 이유 |
|---|---|---|---|---|
| device id |  |  |  |  |
| local user id |  |  |  |  |
| player entity id |  |  |  |  |

## context resolver

| active contexts | focus owner | 허용 action | 차단 action | consumption order |
|---|---|---|---|---|
| Gameplay |  |  |  |  |
| Gameplay + Menu |  |  |  |  |
| TextEntry |  |  |  |  |
| OS focus loss |  |  |  |  |

## command schema

- tick assignment:
- sequence scope:
- axis quantization/sampling:
- edge buffer:
- rejected command evidence:

## cleanup 정책

- focus loss:
- device disconnect:
- local user removal:
- scene unload:

## camera/UI 경계

- camera가 생성하는 intent:
- UI가 생성하는 intent:
- authoritative result의 owner:
- optimistic presentation correction:
