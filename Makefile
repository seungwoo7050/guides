.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/check_structure.py
	python3 scripts/check_links.py
	python3 scripts/check_profiles.py

verify:
	./verify.sh

clean:
	rm -rf .guide __pycache__
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
