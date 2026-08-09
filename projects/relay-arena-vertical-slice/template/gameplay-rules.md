# Gameplay rules

## match state machine

| phase | enter trigger | allowed commands | exit trigger | durable side effect | invariant |
|---|---|---|---|---|---|
| loading |  |  |  |  |  |
| countdown |  |  |  |  |  |
| playing |  |  |  |  |  |
| result_pending |  |  |  |  |  |
| result_committed |  |  |  |  |  |

## command decisions

| command | precondition | accepted transition/event | reject reason | idempotency |
|---|---|---|---|---|
| Move |  |  |  |  |
| Dash |  |  |  |  |
| Interact |  |  |  |  |

## progression commit

- result identity:
- best-time compare:
- durable commit owner:
- duplicate/suspend retry:
- UI notification relation:
