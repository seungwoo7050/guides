.PHONY: prepare check docs-check examples-check exercises-check capstone-check validator-check external-links-check verify clean

PYTHON ?= python3

prepare:
	./prepare.sh

check: docs-check examples-check exercises-check capstone-check validator-check

docs-check:
	$(PYTHON) scripts/check_docs.py

examples-check:
	$(PYTHON) -m unittest discover -s examples/tests -v

exercises-check:
	$(PYTHON) scripts/check_learning_contracts.py --scope exercises

capstone-check:
	$(PYTHON) scripts/check_learning_contracts.py --scope capstone

validator-check:
	$(PYTHON) scripts/test_verifier.py
	$(PYTHON) scripts/test_workspace_tools.py
	$(PYTHON) scripts/test_verify_safety.py

# Network access is intentionally outside `check` and `verify`.
external-links-check:
	$(PYTHON) scripts/check_external_links.py

verify:
	./verify.sh

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; root=Path('.'); [shutil.rmtree(p) for p in list(root.rglob('__pycache__')) if p.is_dir()]; [p.unlink() for p in list(root.rglob('*.pyc')) if p.is_file()]"
