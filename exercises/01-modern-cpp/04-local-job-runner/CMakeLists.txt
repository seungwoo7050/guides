add_library(local_job_runner_reference reference/src/job_runner.cpp)
target_include_directories(local_job_runner_reference PUBLIC reference/include)
target_link_libraries(
    local_job_runner_reference
    PUBLIC
        guide_modern_options
        Threads::Threads
    PRIVATE
        guide_modern_warnings
)

add_library(local_job_runner_skeleton skeleton/src/job_runner.cpp)
target_include_directories(local_job_runner_skeleton PUBLIC skeleton/include)
target_link_libraries(
    local_job_runner_skeleton
    PUBLIC
        guide_modern_options
        Threads::Threads
    PRIVATE
        guide_modern_warnings
)


add_executable(local_job_runner_reference_app app/main.cpp)
target_link_libraries(
    local_job_runner_reference_app
    PRIVATE
        local_job_runner_reference
        guide_modern_warnings
)

add_executable(local_job_runner_skeleton_app app/main.cpp)
target_link_libraries(
    local_job_runner_skeleton_app
    PRIVATE
        local_job_runner_skeleton
        guide_modern_warnings
)

add_executable(local_job_runner_reference_tests tests/job_runner_tests.cpp)
target_include_directories(
    local_job_runner_reference_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    local_job_runner_reference_tests
    PRIVATE
        local_job_runner_reference
        guide_modern_warnings
)

add_executable(local_job_runner_skeleton_tests tests/job_runner_tests.cpp)
target_include_directories(
    local_job_runner_skeleton_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    local_job_runner_skeleton_tests
    PRIVATE
        local_job_runner_skeleton
        guide_modern_warnings
)

add_test(NAME modern.local-job-runner COMMAND local_job_runner_reference_tests)
set_tests_properties(modern.local-job-runner PROPERTIES TIMEOUT 20)

add_test(
    NAME modern.local-job-runner.app
    COMMAND
        local_job_runner_reference_app
        ${CMAKE_CURRENT_BINARY_DIR}/local-job-runner-demo.tsv
)
set_tests_properties(
    modern.local-job-runner.app
    PROPERTIES
        TIMEOUT 20
        PASS_REGULAR_EXPRESSION "1 succeeded compile-ready"
)

if(GUIDE_TEST_SKELETONS)
    add_test(
        NAME modern.learner.local-job-runner
        COMMAND local_job_runner_skeleton_tests
    )
    set_tests_properties(modern.learner.local-job-runner PROPERTIES TIMEOUT 20)
    add_test(
        NAME modern.learner.local-job-runner.app
        COMMAND
            local_job_runner_skeleton_app
            ${CMAKE_CURRENT_BINARY_DIR}/local-job-runner-learner.tsv
    )
    set_tests_properties(
        modern.learner.local-job-runner.app
        PROPERTIES
            TIMEOUT 20
            PASS_REGULAR_EXPRESSION "1 succeeded compile-ready"
    )
endif()
