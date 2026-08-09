# Route와 Authorization 조사 메모

이 문서는 source review에서 추출한 의사코드와 테스트 목록입니다. 실제 실행 결과는 [`verification-observations.json`](verification-observations.json)에 있습니다.

## Report 조회

```text
GET /api/reports/{report_id}

report = reportRepository.findByIdAndOwner(report_id, currentUser.id)
if report is missing:
    return 404
return report metadata
```

## Download URL 발급

```text
POST /api/reports/{report_id}/download

report = reportRepository.findCompletedById(report_id)
if report is missing:
    return 404
return objectSigner.sign(report.object_key, expires=10 minutes)
```

route middleware는 authenticated session을 요구합니다. 이 메모에는 download handler가 `currentUser.id`를 사용하는 코드가 보이지 않습니다. repository의 다른 layer에서 owner가 제한되는지는 제공 자료만으로 확인해야 합니다.

## Worker transaction 조회

```text
POST /internal/report-data
claims: service_id, credential_id, job_id
body: account_id, range

job = reportJobRepository.find(job_id)
if job is missing or job.account_id != body.account_id:
    deny
return transactions(job.account_id, range)
```

## Object proxy

```text
READ /internal/objects/{object_key}
WRITE /internal/objects/{object_key}

policyDecision(service_id, action, object_key, environment)
```

현재 policy snapshot의 worker resource는 `ledgerlab-reports/*`입니다. job·tenant prefix를 enforcement input으로 전달하는지는 event와 policy 자료를 함께 확인합니다.

## 알려진 테스트 이름

- `report_metadata_rejects_other_owner`
- `download_requires_completed_report`
- `worker_report_data_matches_job_account`
- `signed_url_expires_after_ten_minutes`
- `object_proxy_denies_production_bucket`

테스트 이름만으로 assertion과 runtime build를 단정하지 않습니다.
