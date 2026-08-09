# Dataset 계약과 문서화

Dataset은 모델에 넣는 CSV 파일이 아니다. **어떤 세계에서 어떤 절차로 관측·선택·변환·labeling된 기록의 특정 version**이다. 모델이 학습한 것은 현실 자체가 아니라 이 생성 과정에 남은 패턴이다.

## 1. Dataset의 정체성

최소한 다음으로 dataset version을 식별한다.

```text
source snapshot 또는 query version
+ 수집 기간
+ 포함·제외 기준
+ schema version
+ label definition version
+ transformation code version
+ row count와 content digest
```

파일 이름 `train_final_v2.csv`는 정체성이 아니다. 같은 이름으로 내용이 바뀌거나 같은 내용이 여러 이름으로 복제될 수 있다.

## 2. Row unit과 key

각 row가 무엇인지 한 문장으로 설명한다.

예:

```text
한 row는 월요일 00:00 기준 활성 유료 계정 하나의 예측 snapshot이다.
```

그 다음 key를 고정한다.

- entity key: 어떤 실제 대상을 나타내는가
- observation key: 같은 entity의 여러 시점을 어떻게 구분하는가
- event key: 중복 수집을 어떻게 찾는가
- label key: 어느 observation에 어느 outcome을 연결하는가

key가 없으면 duplicate, group split과 label join 오류를 검증하기 어렵다.

## 3. Provenance

각 column마다 다음을 기록한다.

| 항목 | 설명 |
|---|---|
| source | 원본 시스템·테이블·event·파일 |
| producer | 누가 또는 어떤 서비스가 생성하는가 |
| semantic | 값이 실제로 의미하는 것 |
| availability | 예측 시점에 언제 조회 가능한가 |
| transformation | 집계·정규화·mapping 과정 |
| missingness | 왜 비어 있을 수 있는가 |
| retention | 얼마나 오래 보존되는가 |
| sensitivity | 개인정보·비밀·규제 데이터 여부 |

feature 이름만 보고 의미를 추측하지 않는다. `last_active_at`가 client clock인지 server receipt time인지에 따라 시간 누출 여부가 달라질 수 있다.

## 4. 포함과 제외

Dataset은 현실의 표본을 선택한다. 다음 조건을 명시한다.

- 시간 범위
- 지역·제품·계정 상태
- 최소 관측 기간
- 삭제·정지·테스트 계정 처리
- label이 아직 확정되지 않은 observation 처리
- 중복과 충돌 해결 규칙
- 데이터 품질 문제로 제외한 row

제외한 집단은 모델의 비범위가 될 수 있다. 학습 시 제외하고 운영에서는 입력하는 상태가 가장 위험하다.

## 5. Label은 관측 절차다

Label 정의에는 값뿐 아니라 관측 과정을 포함한다.

```text
label 의미
label을 만든 원천 사건
확정 시점
관측 지연
수정·취소 가능성
누락되는 조건
사람 annotation 지침
annotator 간 불일치 처리
```

### 자연적으로 기록되는 label

구매 완료, 장치 고장처럼 시스템 event에서 계산할 수 있다. 그래도 event 누락, 취소와 늦은 도착을 확인해야 한다.

### 사람이 붙이는 label

annotation guideline, 예시, 모호한 사례, annotator 배정, 합의 과정과 품질 검사가 필요하다. 사람 label을 절대적인 진실로 취급하지 않는다.

### Proxy label

실제 목표 대신 관측 가능한 대리값을 사용한다. proxy와 목표 사이의 차이를 문서화하고 중요한 slice에서 검증한다.

### 선택적으로만 관측되는 label

대출 승인자에게만 상환 결과가 존재하거나 검사받은 환자에게만 진단이 있다면 label이 무작위로 누락되지 않는다. 모델은 기존 정책의 선택을 학습할 수 있다.

## 6. Missing value는 하나의 값이 아니다

빈 값은 여러 상태를 압축할 수 있다.

- 측정하지 않음
- 측정할 수 없음
- 적용 대상 아님
- 수집 실패
- 아직 도착하지 않음
- privacy 정책으로 삭제
- 원래 시스템에 값이 없음

모든 누락을 평균으로 채우기 전에 원인을 구분한다. missing indicator가 유용할 수 있지만, 운영 과정의 장애나 차별적 접근을 feature로 굳힐 수도 있다.

## 7. 대표성과 coverage

Dataset이 목표 모집단을 어느 정도 덮는지 확인한다.

- 시간대와 계절
- 지역과 언어
- 장치·제품 version
- 신규·기존 사용자
- 드문 class와 극단값
- 중요한 보호 집단 또는 업무 slice
- 운영 장애와 비정상 상태

전체 분포의 비율만 보지 않는다. 작은 집단은 평균에서 사라질 수 있다. 각 slice의 row 수, label rate와 missing rate를 함께 본다.

## 8. Dataset quality와 model quality를 분리한다

Dataset 검사는 모델 학습 전에 실행할 수 있어야 한다.

### Schema

- column 이름과 type
- 허용 범위와 category
- nullability
- key uniqueness
- timestamp timezone

### 관계

- observation time < label time
- entity와 observation key 일관성
- join 후 row count 변화
- split 간 entity 중복 없음

### 분포

- row count와 label prevalence
- category coverage
- missing·duplicate rate
- 기간별 변화

### Content fingerprint

작은 fixture는 전체 digest를 고정할 수 있다. 큰 dataset은 manifest, partition digest와 source snapshot ID를 기록한다.

검사 통과는 대표성이나 label 타당성을 증명하지 않는다. 기계 검사는 구조적 계약을, dataset review는 생성 과정과 사용 제한을 검토한다.

## 9. Dataset documentation

Dataset card 또는 datasheet에는 다음을 포함한다.

1. 동기와 사용 목적
2. dataset 구성과 row unit
3. 수집·선택·labeling 과정
4. preprocessing과 version
5. 권장 split
6. 알려진 누락·편향·대표성 한계
7. 개인정보·동의·라이선스·보존
8. 권장 사용과 금지 사용
9. 유지보수 담당자와 변경 기록

Template은 [`dataset-card.md`](../../exercises/model-lifecycle/templates/dataset-card.md)에 있다.

## 10. 개인정보와 사용 권한

모델 품질과 별개로 확인한다.

- 수집 목적과 학습 목적이 일치하는가
- 동의·계약·법적 근거가 있는가
- 필요하지 않은 식별자를 제거했는가
- 민감정보와 파생 feature를 누가 볼 수 있는가
- 삭제 요청이 dataset과 artifact에 어떻게 반영되는가
- 외부 dataset의 라이선스가 모델 배포를 허용하는가
- dataset을 제3자와 공유할 수 있는가

익명화했다는 주장만으로 안전하지 않다. 다른 정보와 결합한 재식별 가능성과 rare category를 고려한다.

## 11. Version change

Dataset version이 바뀌면 다음을 비교한다.

```text
row 추가·삭제 이유
schema와 category 변화
label definition 변화
source system 변화
기간과 모집단 변화
split 재생성 여부
기존 model과 평가 결과의 비교 가능성
```

label 정의가 바뀌었다면 단순한 데이터 추가가 아니다. 이전 실험과 같은 target을 학습하지 않을 수 있다.

## 12. 대표적인 실패

### Convenience dataset

쉽게 구할 수 있다는 이유로 실제 모집단과 다른 dataset을 사용하고 제품 가능성을 주장한다.

### Post-treatment feature

action 이후 생성된 feature를 포함해 미래를 누출한다.

### Silent relabeling

업무 규칙이 바뀌었는데 같은 column 이름을 유지해 서로 다른 label version을 섞는다.

### CSV가 정본

source query와 transformation code 없이 export 파일만 남겨 재생성할 수 없다.

### Dataset size만 강조

row 수가 많아도 중복 entity, 낮은 label 품질과 좁은 모집단이면 독립 정보가 적다.

## 13. 리뷰 질문

- 한 row와 key를 정확히 설명할 수 있는가?
- feature와 label은 예측 시점에 실제로 이용 가능한가?
- 포함되지 않은 집단은 누구이며 운영 입력에서 차단되는가?
- label 누락과 오류는 어떤 정책이나 사람 행동과 연결되는가?
- 같은 dataset version을 재생성할 source·code·manifest가 있는가?
- 개인정보·라이선스·삭제 요구를 model lifecycle에 반영할 수 있는가?
- 중요한 slice의 row 수와 label rate가 충분한가?
- dataset change가 기존 평가와 호환되는가?

## 실습 연결

누적 실습 2단계에서는 합성 dataset의 generator, committed CSV, schema와 split manifest를 검토한다. `entity_id`가 split 사이에 겹치지 않는지, row key가 유일한지, generator가 동일한 bytes를 다시 만드는지 검사한다.
