SHELL := /bin/sh
PYTHON ?= python3
EXERCISE_IMPL ?= skeleton
TEST_MODULE := tests.test_processor_model

STAGE_01_TESTS := $(TEST_MODULE).BitsTests
STAGE_02_TESTS := $(STAGE_01_TESTS) $(TEST_MODULE).IsaTests
STAGE_03_TESTS := $(STAGE_02_TESTS) $(TEST_MODULE).PerformanceTests
STAGE_04_TESTS := $(STAGE_03_TESTS) $(TEST_MODULE).ControlTests
STAGE_05_TESTS := $(STAGE_04_TESTS) $(TEST_MODULE).PipelineTests
STAGE_06_TESTS := $(STAGE_05_TESTS) $(TEST_MODULE).CacheTests
STAGE_07_TESTS := $(STAGE_06_TESTS) $(TEST_MODULE).VirtualMemoryTests
STAGE_08_TESTS := $(STAGE_07_TESTS) $(TEST_MODULE).BranchPredictorTests \
	$(TEST_MODULE).ReorderBufferTests
STAGE_10_TESTS := $(STAGE_08_TESTS) $(TEST_MODULE).CoherenceTests

.PHONY: check verify observe validate-impl skeleton-check reference-check \
	exercise-test stage-01 stage-02 stage-03 stage-04 stage-05 stage-06 \
	stage-07 stage-08 stage-09 stage-10 test clean

check: skeleton-check reference-check

verify: check

validate-impl:
	@case "$(EXERCISE_IMPL)" in \
		skeleton|reference|workspace) ;; \
		*) printf '%s\n' 'EXERCISE_IMPL은 skeleton, reference 또는 workspace여야 합니다.' >&2; exit 2 ;; \
	esac
	@[ -d "$(EXERCISE_IMPL)" ] || { \
		printf '%s\n' "구현 디렉터리가 없습니다: $(EXERCISE_IMPL)" >&2; \
		exit 2; \
	}

skeleton-check:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m compileall -q skeleton
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) skeleton/processor-model.py --help >/dev/null
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) check.py --skeleton

reference-check:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) check.py --reference

exercise-test: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest discover -s tests -v

stage-01: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_01_TESTS) -v

stage-02: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_02_TESTS) -v

stage-03: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_03_TESTS) -v

stage-04: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_04_TESTS) -v

stage-05: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_05_TESTS) -v

stage-06: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_06_TESTS) -v

stage-07: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_07_TESTS) -v

stage-08: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_08_TESTS) -v

stage-09:
	@$(MAKE) -C ../.. stage-09

stage-10: validate-impl
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON) -m unittest $(STAGE_10_TESTS) -v

test: reference-check

observe:
	@$(PYTHON) reference/processor-model.py bits add 127 1 --width 8
	@$(PYTHON) reference/processor-model.py isa fixtures/programs/sum.asm --max-steps 100
	@$(PYTHON) reference/processor-model.py pipeline fixtures/traces/pipeline-load-use.trace --forwarding full
	@$(PYTHON) reference/processor-model.py cache fixtures/traces/cache.trace --size 16 --block 4 --ways 1
	@$(PYTHON) reference/processor-model.py vm fixtures/vm/config.json fixtures/vm/trace.txt
	@$(PYTHON) reference/processor-model.py coherence fixtures/traces/coherence-false-sharing.trace --cores 2 --line-size 64

clean:
	@find . -type d -name workspace -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type d -name workspace -prune -o -type f -name '*.py[co]' -exec rm -f {} +
