.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/check_docs.py

verify:
	./verify.sh

clean:
	rm -rf .guide
