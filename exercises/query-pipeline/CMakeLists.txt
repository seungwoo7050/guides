cmake_minimum_required(VERSION 3.20)
project(query_pipeline LANGUAGES CXX)

add_library(query_pipeline src/query.cpp)
target_include_directories(query_pipeline PUBLIC include)
target_compile_features(query_pipeline PUBLIC cxx_std_20)
target_compile_options(query_pipeline PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(query_pipeline_tests tests/query_tests.cpp)
target_link_libraries(query_pipeline_tests PRIVATE query_pipeline)
target_compile_features(query_pipeline_tests PRIVATE cxx_std_20)
target_compile_options(query_pipeline_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_test(NAME query_pipeline_tests COMMAND query_pipeline_tests)
