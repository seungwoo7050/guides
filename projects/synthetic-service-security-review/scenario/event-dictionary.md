# LedgerLab Event Dictionary

| Event | 주요 producer | 현재 field | 알려진 한계 |
|---|---|---|---|
| `session.authenticated` | gateway | `event_id`, `user_id`, `session_id`, `request_id`, `outcome` | workload delegation ID 없음 |
| `report.download_requested` | account API | `request_id`, `report_id`, `user_id`, `outcome` | owner ID·authorization policy ID 없음 |
| `credential.issued` | job broker | `credential_id`, `service_id`, `job_id`, `expires_at` | tenant·object prefix 없음 |
| `object.read` | object proxy | `service_id`, `credential_id`, `object_key`, `outcome` | user·job·policy·owner가 optional |
| `package.resolved` | package proxy | `build_id`, `name`, `version`, `namespace`, `digest` | expected namespace·expected digest 없음 |
| `tag.updated` | registry | `tag`, `old_digest`, `new_digest`, `actor` | actor delegation chain 없음 |
| `deployment.started` | deployer | `service`, `requested_reference`, `release_id` | resolved digest 없음 |
| `deployment.ready` | deployer | `service`, `release_id`, `outcome` | runtime digest·policy version 없음 |
| `alert.opened` | detector | `alert_id`, `rule_id`, `correlation_ids` | 원본 event가 별도 query 필요 |
| `incident.action` | incident tool | `action`, `actor`, `target`, `reason` | decision ID가 optional |

## 전달 특성

- event는 적어도 한 번 전달되므로 중복될 수 있습니다.
- producer clock 차이는 최대 ±30초로 추정되지만 측정 event가 없습니다.
- ingest 지연은 일반적으로 10초 이내, 장애 중 최대 5분입니다.
- 원본 event는 30일, 정규화 event는 180일 보존됩니다.
- 정규화 실패 event는 dead-letter partition으로 이동하지만 현재 alert가 없습니다.
