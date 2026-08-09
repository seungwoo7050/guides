# Movement and space contract

## coordinate spaces

| value | source space | destination space | conversion owner | validation |
|---|---|---|---|---|
| input move |  |  |  |  |
| player transform |  |  |  |  |
| camera aim |  |  |  |  |
| navigation path |  |  |  |  |

## simulation order

```text
commands
→ movement intent
→ collision query
→ authoritative transform
→ gameplay contact events
→ presentation interpolation
```

- fixed/variable phase:
- teleport/checkpoint reset:
- dash collision policy:
- hazard event ordering:
- transform writer:

## failure cases

| case | invariant | expected result | trace/profile |
|---|---|---|---|
| low/high render FPS |  |  |  |
| tunneling candidate |  |  |  |
| scene origin/parent change |  |  |  |
| network correction |  |  |  |
