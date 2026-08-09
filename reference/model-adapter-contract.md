# Model adapter contract template

## Adapter identity

```text
name:
version:
provider:
model profile:
```

## Request

| Field | Type | Required | Meaning | Sensitive |
|---|---|---:|---|---:|
| request_id |  |  |  |  |
| session_id |  |  |  |  |
| instruction_blocks |  |  |  |  |
| context_items |  |  |  |  |
| tool_definitions |  |  |  |  |
| deadline |  |  |  |  |

## Streaming events

| Event | Ordering rule | Durable? | UI? |
|---|---|---:|---:|

## Action candidate

```text
action ID:
tool:
arguments schema:
purpose field:
validation:
```

## Error taxonomy

| Error | Retryable | Session effect | User visible |
|---|---:|---|---:|

## Cancellation

## Usage and cost receipt

## Provider-state independence

## Scripted scenarios
