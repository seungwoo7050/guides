.PHONY: prepare check verify fixtures example workspace submission capstone meta clean

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

submission:
	@test -n "$(EXERCISE)" || (echo "usage: make submission EXERCISE=01 SUBMISSION=/absolute/path" >&2; exit 2)
	@test -n "$(SUBMISSION)" || (echo "usage: make submission EXERCISE=01 SUBMISSION=/absolute/path" >&2; exit 2)
	python3 scripts/check_submission.py --exercise "$(EXERCISE)" --submission "$(SUBMISSION)"

capstone:
	python3 projects/relay-arena-vertical-slice/tests/check_contract.py --implementation projects/relay-arena-vertical-slice/reference/relay_arena.py

meta:
	python3 scripts/check_submission.py --self-test
	python3 projects/relay-arena-vertical-slice/tests/check_mutants.py

clean:
	python3 scripts/cleanup.py
