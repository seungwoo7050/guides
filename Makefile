SHELL := /bin/sh
PYTHON ?= python3

.PHONY: prepare check static meta verify verify-foundations verify-production \
	verify-repeatability clean

prepare:
	./prepare.sh

# Docker 없이 빠르게 확인할 수 있는 문서·검증기·운영 실습 계약입니다.
check: static meta verify-production

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
	@find exercises -type f \( \
		-name '*.log' -o \
		-name '*.pid' -o \
		-name '*.crt' -o \
		-name '*.key' -o \
		-name '*.pyc' \
	\) -delete 2>/dev/null || true
	@find exercises -type d \( \
		-name '__pycache__' -o \
		-name '.pytest_cache' \
	\) -prune -exec rm -rf {} + 2>/dev/null || true
	@find exercises -type f -path '*/secrets/*.txt' \
		! -name '*.txt.example' -delete 2>/dev/null || true
	@find exercises -type f -path '*/backups/*' -delete 2>/dev/null || true
	@find exercises -type d \( -name secrets -o -name backups \) \
		-empty -delete 2>/dev/null || true
