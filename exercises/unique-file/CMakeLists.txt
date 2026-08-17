cmake_minimum_required(VERSION 3.20)
project(unique_file LANGUAGES CXX)

add_library(unique_file src/unique_file.cpp)
target_include_directories(unique_file PUBLIC include)
target_compile_features(unique_file PUBLIC cxx_std_20)
target_compile_options(unique_file PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(unique_file_tests tests/unique_file_tests.cpp)
target_link_libraries(unique_file_tests PRIVATE unique_file)
target_compile_features(unique_file_tests PRIVATE cxx_std_20)
target_compile_options(unique_file_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_test(NAME unique_file_tests COMMAND unique_file_tests)
