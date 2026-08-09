PYTHON ?= python3
WORKSPACE ?= .workspaces/mica

.PHONY: help prepare check verify structure links docs capstone examples capstone-start workspace clean

help:
	@printf '%s\n' \
	  'make prepare         환경과 source fingerprint 준비' \
	  'make check           문서·명세·예제 빠른 검사' \
	  'make verify          임시 복사본에서 전체 검증' \
	  'make workspace       Mica skeleton workspace 생성' \
	  'make capstone-start  skeleton의 의도된 초기 실패 확인' \
	  'make clean           준비 marker, 기본 workspace와 Python cache 제거'

prepare:
	./prepare.sh

structure:
	$(PYTHON) scripts/check_structure.py

links:
	$(PYTHON) scripts/check_links.py

docs:
	$(PYTHON) scripts/check_docs.py

capstone:
	$(PYTHON) scripts/check_capstone_spec.py

examples:
	$(PYTHON) scripts/run_examples.py

check: structure links docs capstone examples

verify:
	./verify.sh

capstone-start:
	$(PYTHON) exercises/08-mica-capstone/check_submission.py \
	  --workspace exercises/08-mica-capstone/skeleton \
	  --stage skeleton

workspace:
	./scripts/new-workspace.sh $(WORKSPACE)

clean:
	rm -rf .guide .workspaces
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
