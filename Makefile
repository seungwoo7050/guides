.PHONY: prepare check verify fixtures example workspace clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify.py --quick

verify:
	./verify.sh

fixtures:
	python3 scripts/verify.py --fixtures-only

example:
	python3 examples/fixed-step-replay/sim.py --verify --pretty

workspace:
	@test -n "$(DEST)" || (echo "usage: make workspace DEST=/absolute/new/path" >&2; exit 2)
	./scripts/new-workspace.sh "$(DEST)"

clean:
	python3 scripts/cleanup.py
