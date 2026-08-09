.PHONY: prepare check docs-check examples-check validator-check verify clean

PYTHON ?= python3

prepare:
	./prepare.sh

check: docs-check examples-check

docs-check:
	$(PYTHON) scripts/check_docs.py

examples-check:
	$(PYTHON) -m unittest discover -s examples/tests -v

validator-check:
	$(PYTHON) scripts/test_verifier.py

verify:
	./verify.sh

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; root=Path('.'); [shutil.rmtree(p) for p in list(root.rglob('__pycache__')) if p.is_dir()]; [p.unlink() for p in list(root.rglob('*.pyc')) if p.is_file()]"
