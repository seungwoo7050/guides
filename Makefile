.PHONY: prepare render check verify clean

PYTHON ?= python3

prepare:
	PYTHON="$(PYTHON)" ./prepare.sh

render:
	"$(PYTHON)" scripts/render_catalog.py

check:
	"$(PYTHON)" scripts/check_catalog.py
	"$(PYTHON)" scripts/render_catalog.py --check
	"$(PYTHON)" scripts/check_links.py

verify:
	PYTHON="$(PYTHON)" ./verify.sh

clean:
	rm -rf .guide
