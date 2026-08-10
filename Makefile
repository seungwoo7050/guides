PYTHON ?= python3
WORKSPACE ?= .workspaces/mica

.PHONY: help prepare check verify structure links docs learning capstone examples labs capstone-start workspace clean purge-workspace

help:
	@printf '%s\n' \
	  'make prepare         환경과 source fingerprint 준비' \
	  'make check           문서·명세·예제 빠른 검사' \
	  'make verify          임시 복사본에서 전체 검증' \
	  'make labs            단계 실습 reference evidence 검사' \
	  'make learning        owns→evidence→exit 추적성 검사' \
	  'make workspace       Mica skeleton workspace 생성' \
	  'make capstone-start  skeleton의 의도된 초기 실패 확인' \
	  'make clean           준비 marker와 생성 cache 제거(workspace 보존)' \
	  'make purge-workspace WORKSPACE=.workspaces/name  지정 workspace 제거'

prepare:
	./prepare.sh

structure:
	$(PYTHON) scripts/check_structure.py

links:
	$(PYTHON) scripts/check_links.py

docs:
	$(PYTHON) scripts/check_docs.py

learning:
	$(PYTHON) scripts/check_learning_contract.py

capstone:
	$(PYTHON) scripts/check_capstone_spec.py

examples:
	$(PYTHON) scripts/run_examples.py

labs:
	$(PYTHON) scripts/run_labs.py

check: structure links docs learning capstone examples labs

verify:
	./verify.sh

capstone-start:
	$(PYTHON) exercises/08-mica-capstone/check_submission.py \
	  --workspace exercises/08-mica-capstone/skeleton \
	  --stage skeleton

workspace:
	./scripts/new-workspace.sh $(WORKSPACE)

clean:
	$(PYTHON) scripts/clean_generated.py

purge-workspace:
	$(PYTHON) scripts/purge_workspace.py "$(WORKSPACE)"
