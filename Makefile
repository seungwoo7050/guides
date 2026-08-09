.PHONY: prepare check verify lab-quality tooling-test capstone clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify_repository.py

verify:
	./verify.sh

lab-quality:
	python3 exercises/07-isolated-attack-path/tests/check_quality.py

tooling-test:
	python3 scripts/test_tooling.py

capstone:
	python3 scripts/verify_capstone.py projects/synthetic-service-security-review/work

clean:
	rm -rf .guide
