add_library(query_pipeline_reference reference/src/query.cpp)
target_include_directories(query_pipeline_reference PUBLIC reference/include)
target_link_libraries(query_pipeline_reference PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_library(query_pipeline_skeleton skeleton/src/query.cpp)
target_include_directories(query_pipeline_skeleton PUBLIC skeleton/include)
target_link_libraries(query_pipeline_skeleton PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_executable(query_pipeline_reference_tests tests/query_tests.cpp)
target_include_directories(
    query_pipeline_reference_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    query_pipeline_reference_tests
    PRIVATE
        query_pipeline_reference
        guide_modern_warnings
)

add_executable(query_pipeline_skeleton_tests tests/query_tests.cpp)
target_include_directories(
    query_pipeline_skeleton_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    query_pipeline_skeleton_tests
    PRIVATE
        query_pipeline_skeleton
        guide_modern_warnings
)

add_test(NAME modern.query-pipeline COMMAND query_pipeline_reference_tests)
set_tests_properties(modern.query-pipeline PROPERTIES TIMEOUT 20)

if(GUIDE_TEST_SKELETONS)
    add_test(NAME modern.learner.query-pipeline COMMAND query_pipeline_skeleton_tests)
    set_tests_properties(modern.learner.query-pipeline PROPERTIES TIMEOUT 20)
endif()
