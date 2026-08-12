SHELL := /bin/sh
PREPARED_PYTHON := .verify/venv/bin/python
PYTHON ?= $(if $(wildcard $(PREPARED_PYTHON)),$(PREPARED_PYTHON),python3)

.PHONY: prepare check static meta verify verify-foundations verify-production \
	verify-repeatability workspace-check evidence-check clean

prepare:
	./prepare.sh

# Docker 없이 빠르게 확인할 수 있는 문서·검증기·운영 실습 계약입니다.
check: static meta workspace-check evidence-check verify-production

workspace-check:
	$(PYTHON) -B scripts/test-workspace.py

evidence-check:
	$(PYTHON) -B exercises/07-troubleshooting/check-evidence.py --self-test

static:
	$(PYTHON) -B scripts/static-verify.py

meta:
	$(PYTHON) -B scripts/meta-verify.py

# 저장소 루트의 정식 전체 검증 진입점입니다.
verify:
	./verify.sh

verify-foundations:
	PYTHON="$(PYTHON)" ./scripts/verify-all.sh foundations

verify-production:
	PYTHON="$(PYTHON)" ./scripts/verify-all.sh production

verify-repeatability:
	PYTHON="$(PYTHON)" ./scripts/verify-all.sh repeatability

clean:
	@find exercises -type d \( -name workspace -o -name '.workspace.tmp.*' \) -prune -o -type f \( \
		-name '*.log' -o \
		-name '*.pid' -o \
		-name '*.crt' -o \
		-name '*.key' -o \
		-name '*.pyc' \
	\) -exec rm -f -- {} + 2>/dev/null || true
	@find exercises -type d \( -name workspace -o -name '.workspace.tmp.*' \) -prune -o -type d \( \
		-name '__pycache__' -o \
		-name '.pytest_cache' \
	\) -prune -exec rm -rf {} + 2>/dev/null || true
	@find exercises -type d \( -name workspace -o -name '.workspace.tmp.*' \) -prune -o -type f -path '*/secrets/*.txt' \
		! -name '*.txt.example' -exec rm -f -- {} + 2>/dev/null || true
	@find exercises -type d \( -name workspace -o -name '.workspace.tmp.*' \) -prune -o -type f -path '*/backups/*' -exec rm -f -- {} + 2>/dev/null || true
	@find exercises -type d \( -name workspace -o -name '.workspace.tmp.*' \) -prune -o -type d \( -name secrets -o -name backups \) \
		-empty -exec rmdir -- {} + 2>/dev/null || true
