add_library(unique_file_reference reference/src/unique_file.cpp)
target_include_directories(unique_file_reference PUBLIC reference/include)
target_link_libraries(unique_file_reference PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_library(unique_file_skeleton skeleton/src/unique_file.cpp)
target_include_directories(unique_file_skeleton PUBLIC skeleton/include)
target_link_libraries(unique_file_skeleton PUBLIC guide_modern_options PRIVATE guide_modern_warnings)

add_executable(unique_file_reference_tests tests/unique_file_tests.cpp)
target_include_directories(
    unique_file_reference_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    unique_file_reference_tests
    PRIVATE
        unique_file_reference
        guide_modern_warnings
)

add_executable(unique_file_skeleton_tests tests/unique_file_tests.cpp)
target_include_directories(
    unique_file_skeleton_tests
    PRIVATE
        ${PROJECT_SOURCE_DIR}/support
)
target_link_libraries(
    unique_file_skeleton_tests
    PRIVATE
        unique_file_skeleton
        guide_modern_warnings
)

add_test(NAME modern.unique-file COMMAND unique_file_reference_tests)
set_tests_properties(modern.unique-file PROPERTIES TIMEOUT 20)
