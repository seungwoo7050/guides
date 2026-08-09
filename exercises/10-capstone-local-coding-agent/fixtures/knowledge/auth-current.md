---
source_id: auth-policy
revision: 3
scope: auth-internal
freshness: current
---

Refresh-token consumption must make the unused check and state transition indivisible. A deterministic concurrency test must prove that exactly one consumer succeeds.
