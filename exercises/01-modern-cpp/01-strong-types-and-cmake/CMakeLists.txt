# [Implementation 1] 같은 공개 계약을 가진 reference와 skeleton library를 만들고 하나의 test source를 각각 연결합니다.
add_library(strong_types_reference reference/src/task.cpp)
target_include_directories(strong_types_reference PUBLIC reference/include)
target_link_libraries(strong_types_reference PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_library(strong_types_skeleton skeleton/src/task.cpp)
target_include_directories(strong_types_skeleton PUBLIC skeleton/include)
target_link_libraries(strong_types_skeleton PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_executable(strong_types_reference_tests tests/task_tests.cpp)
target_include_directories(
    strong_types_reference_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    strong_types_reference_tests
    PRIVATE
        strong_types_reference
        guide_modern_warnings
)

add_executable(strong_types_skeleton_tests tests/task_tests.cpp)
target_include_directories(
    strong_types_skeleton_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    strong_types_skeleton_tests
    PRIVATE
        strong_types_skeleton
        guide_modern_warnings
)

add_test(NAME modern.strong-types COMMAND strong_types_reference_tests)
set_tests_properties(modern.strong-types PROPERTIES TIMEOUT 20)

if(GUIDE_TEST_SKELETONS)
    add_test(NAME modern.learner.strong-types COMMAND strong_types_skeleton_tests)
    set_tests_properties(modern.learner.strong-types PROPERTIES TIMEOUT 20)
endif()
