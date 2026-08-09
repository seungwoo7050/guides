# Threat model template

## Assets

## Principals

## Trust boundaries

## Entry points

- user task
- repository content
- issue/history
- model output
- tool output
- dependency/build/test
- external tool/network

## Threats

| Threat | Preconditions | Effect | Detection | Prevention | Recovery |
|---|---|---|---|---|---|

## Mandatory scenarios

- repository prompt injection
- path traversal and symlink escape
- secret read/exfiltration
- malicious install/test script
- verifier/answer access
- approval replay or mismatch
- effect duplication after crash
- process escape/leak
- Git destructive action
- trace tampering

## Residual risks

## Security evaluation cases
