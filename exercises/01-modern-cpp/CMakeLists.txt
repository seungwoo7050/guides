cmake_minimum_required(VERSION 3.20)

project(guide_cpp_modern_exercises LANGUAGES CXX)

set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)
find_package(Threads REQUIRED)

option(GUIDE_ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(GUIDE_ENABLE_THREAD_SANITIZER "Enable ThreadSanitizer" OFF)
option(GUIDE_WARNINGS_AS_ERRORS "Treat compiler warnings as errors" ON)

if(GUIDE_ENABLE_SANITIZERS AND GUIDE_ENABLE_THREAD_SANITIZER)
    message(FATAL_ERROR "Address/Undefined sanitizers and ThreadSanitizer need separate build directories")
endif()

add_library(guide_modern_options INTERFACE)
target_compile_features(guide_modern_options INTERFACE cxx_std_20)

add_library(guide_modern_warnings INTERFACE)
if(MSVC)
    target_compile_options(guide_modern_warnings INTERFACE /W4 /permissive- /EHsc)
    if(GUIDE_WARNINGS_AS_ERRORS)
        target_compile_options(guide_modern_warnings INTERFACE /WX)
    endif()
else()
    target_compile_options(
        guide_modern_warnings
        INTERFACE
            -Wall
            -Wextra
            -Wpedantic
            -Wconversion
            -Wshadow
    )
    if(GUIDE_WARNINGS_AS_ERRORS)
        target_compile_options(guide_modern_warnings INTERFACE -Werror)
    endif()
endif()

if(GUIDE_ENABLE_SANITIZERS AND NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    message(FATAL_ERROR "GUIDE_ENABLE_SANITIZERS requires GCC or Clang")
endif()
if(GUIDE_ENABLE_THREAD_SANITIZER AND NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    message(FATAL_ERROR "GUIDE_ENABLE_THREAD_SANITIZER requires GCC or Clang")
endif()

if(GUIDE_ENABLE_SANITIZERS)
    target_compile_options(
        guide_modern_options
        INTERFACE
            -fsanitize=address,undefined
            -fno-omit-frame-pointer
    )
    target_link_options(
        guide_modern_options
        INTERFACE
            -fsanitize=address,undefined
            -fno-omit-frame-pointer
    )
elseif(GUIDE_ENABLE_THREAD_SANITIZER)
    target_compile_options(
        guide_modern_options
        INTERFACE
            -fsanitize=thread
            -fno-omit-frame-pointer
    )
    target_link_options(
        guide_modern_options
        INTERFACE
            -fsanitize=thread
            -fno-omit-frame-pointer
    )
endif()

add_subdirectory(01-strong-types-and-cmake)
add_subdirectory(02-unique-file)
add_subdirectory(03-query-pipeline)
add_subdirectory(04-local-job-runner)

add_custom_target(
    modern_skeletons
    DEPENDS
        strong_types_skeleton_tests
        unique_file_skeleton_tests
        query_pipeline_skeleton_tests
        local_job_runner_skeleton_tests
        local_job_runner_skeleton_app
)

add_custom_target(
    modern_references
    DEPENDS
        strong_types_reference_tests
        unique_file_reference_tests
        query_pipeline_reference_tests
        local_job_runner_reference_tests
        local_job_runner_reference_app
)

