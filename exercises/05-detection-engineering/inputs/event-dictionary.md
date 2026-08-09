# ReportFlow 현재 event dictionary

| Event type | Producer | 현재 field | 알려진 한계 |
|---|---|---|---|
| `api.request` | gateway | `time`, `request_id`, `user_id`, `path`, `status` | resource owner와 auth decision 없음 |
| `job.created` | report-api | `time`, `job_id`, `user_id`, `report_id` | caller service identity 없음 |
| `object.read` | object-proxy | `time`, `service_id`, `object_key`, `result` | delegated user와 job 없음 |
| `object.write` | object-proxy | `time`, `service_id`, `object_key`, `result` | auth policy version 없음 |
| `credential.issued` | identity-broker | `time`, `credential_id`, `service_id`, `expires_at` | job scope가 optional |
| `credential.denied` | identity-broker | `time`, `service_id`, `reason` | request correlation 없음 |
| `release.changed` | deployer | `time`, `service`, `image_tag`, `operator` | digest·provenance 없음 |

모든 timestamp는 UTC 문자열이지만 producer clock 차이에 대한 측정은 없습니다. event sink는 중복 전달할 수 있으며 최대 5분 늦게 도착할 수 있습니다.
