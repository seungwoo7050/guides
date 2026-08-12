.PHONY: \
	verify check docs-check workspace \
	modern-verify modern-configure modern-skeleton-build modern-start-state modern-test modern-release modern-sanitize modern-thread-sanitize modern-exercise-test modern-exercise-sanitize modern-exercise-thread-sanitize modern-clean \
	cpp98-verify cpp98-exercise-test skeleton-build test failure-check sanitize clean

OBJECT_MODEL := exercises/02-cpp98-systems/object-model/command-service
GENERIC_PROGRAMMING := exercises/02-cpp98-systems/generic-programming
NETWORKING := exercises/02-cpp98-systems/networking

MODERN := exercises/01-modern-cpp
MODERN_WORKSPACE ?= .workspace/01-modern-cpp
MODERN_LEARNER_BUILD ?= $(MODERN_WORKSPACE)/build/learner
MODERN_LEARNER_CMAKE_FLAGS ?=
MODERN_BUILD ?= $(MODERN)/build/debug
MODERN_RELEASE_BUILD ?= $(MODERN)/build/release
MODERN_SANITIZE_BUILD ?= $(MODERN)/build/sanitize
MODERN_THREAD_SANITIZE_BUILD ?= $(MODERN)/build/thread-sanitize
CMAKE ?= cmake
CTEST ?= ctest
CPP98_WORKSPACE ?= .workspace/02-cpp98-systems

workspace:
	@case "$(TRACK)" in modern|cpp98) ;; \
		*) echo 'usage: make workspace TRACK=modern|cpp98' >&2; exit 2 ;; \
	esac
	@python3 scripts/new_workspace.py "$(TRACK)"

verify: docs-check modern-verify cpp98-verify
	@echo 'cpp: Modern C++와 C++98 전체 검사를 통과했습니다'

check: docs-check modern-verify
	@echo 'cpp: 빠른 문서·Modern C++ 검사를 통과했습니다'

docs-check:
	@python3 scripts/validate_docs.py

modern-verify:
	@$(MAKE) modern-start-state
	@$(MAKE) modern-test
	@$(MAKE) modern-release
	@echo 'modern-cpp: build와 reference test를 통과했습니다'

modern-configure:
	@$(CMAKE) -S $(MODERN) -B $(MODERN_BUILD) \
		-DCMAKE_BUILD_TYPE=Debug \
		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON

modern-skeleton-build: modern-configure
	+@$(CMAKE) --build $(MODERN_BUILD) --target modern_skeletons

modern-start-state: modern-skeleton-build
	@python3 scripts/verify_modern_skeletons.py $(MODERN_BUILD)

modern-test: modern-configure
	+@$(CMAKE) --build $(MODERN_BUILD) --target modern_references
	@$(CTEST) --test-dir $(MODERN_BUILD) --output-on-failure

modern-release:
	@$(CMAKE) -S $(MODERN) -B $(MODERN_RELEASE_BUILD) \
		-DCMAKE_BUILD_TYPE=Release
	+@$(CMAKE) --build $(MODERN_RELEASE_BUILD) --target modern_references
	@$(CTEST) --test-dir $(MODERN_RELEASE_BUILD) --output-on-failure

modern-sanitize:
	@$(CMAKE) -S $(MODERN) -B $(MODERN_SANITIZE_BUILD) \
		-DCMAKE_BUILD_TYPE=Debug \
		-DGUIDE_ENABLE_SANITIZERS=ON
	+@$(CMAKE) --build $(MODERN_SANITIZE_BUILD) --target modern_references
	@$(CTEST) --test-dir $(MODERN_SANITIZE_BUILD) --output-on-failure

modern-thread-sanitize:
	@$(CMAKE) -S $(MODERN) -B $(MODERN_THREAD_SANITIZE_BUILD) \
		-DCMAKE_BUILD_TYPE=Debug \
		-DGUIDE_ENABLE_THREAD_SANITIZER=ON
	+@$(CMAKE) --build $(MODERN_THREAD_SANITIZE_BUILD) --target modern_references
	@$(CTEST) --test-dir $(MODERN_THREAD_SANITIZE_BUILD) --output-on-failure

modern-exercise-test:
	@test -d "$(MODERN_WORKSPACE)" || { \
		echo 'Modern workspace가 없습니다. 먼저 make workspace TRACK=modern을 실행하세요.' >&2; exit 2; \
	}
	@case "$(MODERN_EXERCISE)" in \
		01-strong-types-and-cmake) targets='strong_types_skeleton_tests'; pattern='^modern\.learner\.strong-types$$' ;; \
		02-unique-file) targets='unique_file_skeleton_tests'; pattern='^modern\.learner\.unique-file$$' ;; \
		03-query-pipeline) targets='query_pipeline_skeleton_tests'; pattern='^modern\.learner\.query-pipeline$$' ;; \
		04-local-job-runner) targets='local_job_runner_skeleton_tests local_job_runner_skeleton_app'; pattern='^modern\.learner\.local-job-runner(\.app)?$$' ;; \
		*) echo 'MODERN_EXERCISE에 01-strong-types-and-cmake, 02-unique-file, 03-query-pipeline, 04-local-job-runner 중 하나를 지정하세요.' >&2; exit 2 ;; \
	esac; \
	$(CMAKE) -S "$(MODERN_WORKSPACE)" -B "$(MODERN_LEARNER_BUILD)" \
		-DCMAKE_BUILD_TYPE=Debug -DGUIDE_TEST_SKELETONS=ON $(MODERN_LEARNER_CMAKE_FLAGS) && \
	$(CMAKE) --build "$(MODERN_LEARNER_BUILD)" --target $$targets && \
	$(CTEST) --test-dir "$(MODERN_LEARNER_BUILD)" --output-on-failure -R "$$pattern"

modern-exercise-sanitize:
	@$(MAKE) modern-exercise-test \
		MODERN_EXERCISE="$(MODERN_EXERCISE)" \
		MODERN_LEARNER_BUILD="$(MODERN_WORKSPACE)/build/learner-sanitize" \
		MODERN_LEARNER_CMAKE_FLAGS='-DGUIDE_ENABLE_SANITIZERS=ON'

modern-exercise-thread-sanitize:
	@$(MAKE) modern-exercise-test \
		MODERN_EXERCISE="$(MODERN_EXERCISE)" \
		MODERN_LEARNER_BUILD="$(MODERN_WORKSPACE)/build/learner-thread-sanitize" \
		MODERN_LEARNER_CMAKE_FLAGS='-DGUIDE_ENABLE_THREAD_SANITIZER=ON'

modern-clean:
	@rm -rf $(MODERN)/build

cpp98-verify:
	@$(MAKE) skeleton-build
	@$(MAKE) test
	@$(MAKE) failure-check
	@echo 'cpp98: 기존 객체·STL·네트워크 검사를 통과했습니다'

cpp98-exercise-test:
	@test -d "$(CPP98_WORKSPACE)" || { \
		echo 'C++98 workspace가 없습니다. 먼저 make workspace TRACK=cpp98을 실행하세요.' >&2; exit 2; \
	}
	@case "$(CPP98_EXERCISE)" in \
		object-model/command-service/01-procedural|\
		object-model/command-service/02-value-ownership|\
		object-model/command-service/03-responsibilities|\
		object-model/command-service/04-polymorphism|\
		object-model/command-service/05-errors|\
		generic-programming/template-array|\
		generic-programming/mini-vector|\
		generic-programming/stl-problems/date-lookup|\
		generic-programming/stl-problems/rpn|\
		generic-programming/stl-problems/sorter|\
		networking/line-server|\
		networking/http-server/01-parser|\
		networking/http-server/02-config-router|\
		networking/http-server/03-nonblocking-server|\
		networking/http-server/04-cgi-process|\
		networking/http-server/05-integrated-server) ;; \
		*) echo 'CPP98_EXERCISE에 exercises/02-cpp98-systems 아래의 완전한 실습 상대 경로를 지정하세요.' >&2; exit 2 ;; \
	esac
	@$(MAKE) -C "$(CPP98_WORKSPACE)/$(CPP98_EXERCISE)" exercise-test

skeleton-build:
	@$(MAKE) -C $(OBJECT_MODEL)/01-procedural exercise
	@$(MAKE) -C $(OBJECT_MODEL)/02-value-ownership skeleton/app skeleton/text_buffer_test
	@$(MAKE) -C $(OBJECT_MODEL)/03-responsibilities skeleton/app skeleton/legacy_app
	@$(MAKE) -C $(OBJECT_MODEL)/04-polymorphism skeleton/app
	@$(MAKE) -C $(OBJECT_MODEL)/05-errors skeleton/app
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/template-array skeleton/tests
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/mini-vector skeleton/tests
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems/date-lookup skeleton/date_lookup
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems/rpn skeleton/rpn
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems/sorter skeleton/sorter
	@$(MAKE) -C $(NETWORKING)/line-server skeleton-server
	@$(MAKE) -C $(NETWORKING)/http-server/01-parser skeleton/tests
	@$(MAKE) -C $(NETWORKING)/http-server/02-config-router skeleton/tests
	@$(MAKE) -C $(NETWORKING)/http-server/03-nonblocking-server skeleton/http_server
	@$(MAKE) -C $(NETWORKING)/http-server/04-cgi-process skeleton/cgi_runner
	@$(MAKE) -C $(NETWORKING)/http-server/05-integrated-server skeleton/integrated_http_server
	@$(MAKE) -C $(NETWORKING)/http-server/05-integrated-server start-state

test:
	@$(MAKE) -C $(OBJECT_MODEL)/01-procedural test
	@$(MAKE) -C $(OBJECT_MODEL)/02-value-ownership test
	@$(MAKE) -C $(OBJECT_MODEL)/03-responsibilities test
	@$(MAKE) -C $(OBJECT_MODEL)/03-responsibilities interface-check
	@$(MAKE) -C $(OBJECT_MODEL)/04-polymorphism test
	@$(MAKE) -C $(OBJECT_MODEL)/05-errors test
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/template-array test
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/mini-vector test
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems test
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems randomized-test
	@$(MAKE) -C $(NETWORKING)/line-server test
	@$(MAKE) -C $(NETWORKING)/http-server test

failure-check:
	@$(MAKE) -C $(OBJECT_MODEL)/02-value-ownership fail-copy
	@$(MAKE) -C $(OBJECT_MODEL)/04-polymorphism fail-nonvirtual
	@$(MAKE) -C $(OBJECT_MODEL)/05-errors fail-commit
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/template-array compile-fail
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/mini-vector fail-copy
	@$(MAKE) -C $(NETWORKING)/line-server leak-check
	@$(MAKE) -C $(NETWORKING)/http-server failure-test

sanitize:
	@$(MAKE) clean
	@$(MAKE) CXXFLAGS='-std=c++98 -Wall -Wextra -Werror -pedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer' test
	@$(MAKE) CXXFLAGS='-std=c++98 -Wall -Wextra -Werror -pedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer' failure-check

clean: modern-clean
	@$(MAKE) -C $(OBJECT_MODEL)/01-procedural clean
	@$(MAKE) -C $(OBJECT_MODEL)/02-value-ownership clean
	@$(MAKE) -C $(OBJECT_MODEL)/03-responsibilities clean
	@$(MAKE) -C $(OBJECT_MODEL)/04-polymorphism clean
	@$(MAKE) -C $(OBJECT_MODEL)/05-errors clean
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/template-array clean
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/mini-vector clean
	@$(MAKE) -C $(GENERIC_PROGRAMMING)/stl-problems clean
	@$(MAKE) -C $(NETWORKING)/line-server clean
	@$(MAKE) -C $(NETWORKING)/http-server clean
	@find exercises -type d -name '*.dSYM' -prune -exec rm -rf {} +
