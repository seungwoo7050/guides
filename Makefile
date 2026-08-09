.PHONY: prepare check verify clean list-exercises

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py --quick
	python3 -m unittest discover -s tests -p 'test_*.py'

verify:
	./verify.sh

clean:
	rm -rf .guide __pycache__ tests/__pycache__ examples/__pycache__ scripts/__pycache__
	find exercises -type d -name __pycache__ -prune -exec rm -rf {} +

list-exercises:
	python3 scripts/exercise_tool.py list
