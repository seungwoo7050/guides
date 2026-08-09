.PHONY: prepare check verify ppm-selftest clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify_repository.py --quick

verify:
	./verify.sh

ppm-selftest:
	python3 tools/ppm_diff.py --self-test

clean:
	rm -rf .guide build out
