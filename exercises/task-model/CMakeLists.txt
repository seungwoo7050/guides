cmake_minimum_required(VERSION 3.20)
project(task_model LANGUAGES CXX)

add_library(task_model src/task.cpp)
target_include_directories(task_model PUBLIC include)
target_compile_features(task_model PUBLIC cxx_std_20)
target_compile_options(task_model PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(task_model_tests tests/task_tests.cpp)
target_link_libraries(task_model_tests PRIVATE task_model)
target_compile_features(task_model_tests PRIVATE cxx_std_20)
target_compile_options(task_model_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_test(NAME task_model_tests COMMAND task_model_tests)
