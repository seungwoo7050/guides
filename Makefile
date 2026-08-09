.PHONY: prepare check verify capstone clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify_repository.py --quick

verify:
	./verify.sh

capstone:
	python3 scripts/verify_capstone.py projects/synthetic-service-security-review/work

clean:
	rm -rf .guide
