cmake_minimum_required(VERSION 3.20)
project(computer_graphics_renderer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CG_IMPLEMENTATION "reference" CACHE STRING "reference, starter, or workspace")
set_property(CACHE CG_IMPLEMENTATION PROPERTY STRINGS reference starter workspace)
set(CG_GPU "auto" CACHE STRING "auto, required, or off")
set_property(CACHE CG_GPU PROPERTY STRINGS auto required off)

if(NOT CG_IMPLEMENTATION MATCHES "^(reference|starter|workspace)$")
  message(FATAL_ERROR "CG_IMPLEMENTATION must be reference, starter, or workspace")
endif()
if(NOT CG_GPU MATCHES "^(auto|required|off)$")
  message(FATAL_ERROR "CG_GPU must be auto, required, or off")
endif()
if(CG_IMPLEMENTATION STREQUAL "workspace" AND NOT IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/workspace")
  message(FATAL_ERROR "workspace is missing; run scripts/new-workspace.sh first")
endif()

set(CG_HAS_SDL3 OFF)
if(NOT CG_GPU STREQUAL "off")
  # 3.4.10 is the documented stable compatibility floor for this guide.
  find_package(SDL3 3.4.10 CONFIG QUIET)
  if(SDL3_FOUND)
    set(CG_HAS_SDL3 ON)
  elseif(CG_GPU STREQUAL "required")
    message(FATAL_ERROR "CG_GPU=required but SDL3 was not found")
  endif()
endif()

set(CG_IMPLEMENTATION_DIR "${CMAKE_CURRENT_SOURCE_DIR}/${CG_IMPLEMENTATION}")
set_property(
  DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.metal"
)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.metal" CG_MSL_SOURCE)
configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/common/shader_source.hpp.in"
  "${CMAKE_CURRENT_BINARY_DIR}/generated/cg/shader_source.hpp"
  @ONLY
)
add_library(cg_core STATIC
  common/artifact.cpp
  common/contracts.cpp
  "${CG_IMPLEMENTATION_DIR}/visual.cpp"
  "${CG_IMPLEMENTATION_DIR}/raster.cpp"
  "${CG_IMPLEMENTATION_DIR}/gpu.cpp"
)
target_include_directories(cg_core
  PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include"
  PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated"
)
target_compile_definitions(cg_core PUBLIC CG_HAS_SDL3=$<BOOL:${CG_HAS_SDL3}>)
if(MSVC)
  target_compile_options(cg_core PRIVATE /W4 /permissive-)
else()
  target_compile_options(cg_core PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
endif()
if(CG_HAS_SDL3)
  target_link_libraries(cg_core PUBLIC SDL3::SDL3)
endif()

add_executable(cg_render common/main.cpp)
target_link_libraries(cg_render PRIVATE cg_core)
set_target_properties(cg_render PROPERTIES OUTPUT_NAME "cg-render")

add_executable(cg_tests tests/contracts_test.cpp)
target_link_libraries(cg_tests PRIVATE cg_core)
set_target_properties(cg_tests PROPERTIES OUTPUT_NAME "cg-tests")

include(CTest)
if(BUILD_TESTING)
  add_test(NAME contracts COMMAND cg_tests)
  file(REAL_PATH "${CMAKE_CURRENT_BINARY_DIR}" CG_REAL_BINARY_DIR)

  set(CG_TEST_RUNNER "${CMAKE_CURRENT_BINARY_DIR}/cmake/cg-run-and-assert.cmake")
  file(GENERATE OUTPUT "${CG_TEST_RUNNER}" CONTENT [=[
if(NOT DEFINED CG_TEST_EXECUTABLE OR
   NOT DEFINED CG_TEST_STAGE OR
   NOT DEFINED CG_TEST_SCENE OR
   NOT DEFINED CG_TEST_BACKEND OR
   NOT DEFINED CG_TEST_OUTPUT OR
   NOT DEFINED CG_TEST_EXPECTED_EXIT)
  message(FATAL_ERROR "the renderer behavior test is missing a required argument")
endif()

file(REMOVE_RECURSE "${CG_TEST_OUTPUT}")
execute_process(
  COMMAND "${CG_TEST_EXECUTABLE}"
          --stage "${CG_TEST_STAGE}"
          --scene "${CG_TEST_SCENE}"
          --backend "${CG_TEST_BACKEND}"
          --out "${CG_TEST_OUTPUT}"
          --frames 3
  RESULT_VARIABLE cg_result
  OUTPUT_VARIABLE cg_stdout
  ERROR_VARIABLE cg_stderr
)
if(NOT "${cg_result}" MATCHES "^-?[0-9]+$")
  message(FATAL_ERROR
          "${CG_TEST_STAGE}: renderer did not exit normally: ${cg_result}\n${cg_stdout}${cg_stderr}")
endif()
if(NOT cg_result EQUAL CG_TEST_EXPECTED_EXIT)
  message(FATAL_ERROR
          "${CG_TEST_STAGE}: expected exit ${CG_TEST_EXPECTED_EXIT}, got ${cg_result}\n${cg_stdout}${cg_stderr}")
endif()

if(CG_TEST_EXPECTED_EXIT EQUAL 0)
  set(cg_run_json "${CG_TEST_OUTPUT}/run.json")
  if(NOT EXISTS "${cg_run_json}")
    message(FATAL_ERROR "${CG_TEST_STAGE}: successful run did not produce run.json")
  endif()
  file(READ "${cg_run_json}" cg_payload)
  foreach(cg_field IN ITEMS stage scene backend status)
    string(JSON cg_value ERROR_VARIABLE cg_json_error GET "${cg_payload}" "${cg_field}")
    if(NOT cg_json_error STREQUAL "NOTFOUND")
      message(FATAL_ERROR "${CG_TEST_STAGE}: invalid run.json field ${cg_field}: ${cg_json_error}")
    endif()
    set("cg_actual_${cg_field}" "${cg_value}")
  endforeach()
  if(NOT cg_actual_stage STREQUAL CG_TEST_STAGE OR
     NOT cg_actual_scene STREQUAL CG_TEST_SCENE OR
     NOT cg_actual_backend STREQUAL CG_TEST_BACKEND OR
     NOT cg_actual_status STREQUAL "pass")
    message(FATAL_ERROR
            "${CG_TEST_STAGE}: run.json identity/status mismatch: "
            "stage=${cg_actual_stage} scene=${cg_actual_scene} "
            "backend=${cg_actual_backend} status=${cg_actual_status}")
  endif()

  string(JSON cg_invariant_count ERROR_VARIABLE cg_json_error
         LENGTH "${cg_payload}" invariants)
  if(NOT cg_json_error STREQUAL "NOTFOUND" OR cg_invariant_count LESS 1)
    message(FATAL_ERROR "${CG_TEST_STAGE}: run.json must contain public invariants")
  endif()
  math(EXPR cg_last_invariant "${cg_invariant_count} - 1")
  foreach(cg_index RANGE 0 ${cg_last_invariant})
    string(JSON cg_invariant_name MEMBER "${cg_payload}" invariants ${cg_index})
    string(JSON cg_invariant_value GET "${cg_payload}" invariants "${cg_invariant_name}")
    if(NOT cg_invariant_value)
      message(FATAL_ERROR
              "${CG_TEST_STAGE}: invariant ${cg_invariant_name} is not satisfied")
    endif()
  endforeach()
elseif(CG_TEST_EXPECTED_EXIT EQUAL 3 AND EXISTS "${CG_TEST_OUTPUT}")
  message(FATAL_ERROR
          "${CG_TEST_STAGE}: not-implemented renderer created an artifact directory")
endif()
]=])

  function(add_cg_behavior_test test_name stage scene backend expected_exit)
    set(test_output "${CG_REAL_BINARY_DIR}/ctest-artifacts/${test_name}")
    add_test(
      NAME "${test_name}"
      COMMAND "${CMAKE_COMMAND}"
              "-DCG_TEST_EXECUTABLE=$<TARGET_FILE:cg_render>"
              "-DCG_TEST_STAGE=${stage}"
              "-DCG_TEST_SCENE=${scene}"
              "-DCG_TEST_BACKEND=${backend}"
              "-DCG_TEST_OUTPUT=${test_output}"
              "-DCG_TEST_EXPECTED_EXIT=${expected_exit}"
              -P "${CG_TEST_RUNNER}"
    )
    set_tests_properties("${test_name}" PROPERTIES TIMEOUT 30)
  endfunction()

  if(CG_IMPLEMENTATION STREQUAL "reference")
    add_cg_behavior_test(reference-01-transform-trace
                         01-transform-trace identity-triangle software 0)
    add_cg_behavior_test(reference-02-sampling-and-color
                         02-sampling-and-color corner-marker software 0)
    add_cg_behavior_test(reference-03-triangle-coverage
                         03-triangle-coverage shared-edge-rectangle software 0)
    add_cg_behavior_test(reference-04-perspective-depth-blend
                         04-perspective-depth-blend perspective-checker software 0)
    add_cg_behavior_test(reference-05-textured-lit-scene
                         05-textured-lit-scene textured-lit-scene software 0)
    add_cg_behavior_test(lifecycle-06-gpu-first-frame
                         06-gpu-first-frame shared-textured-triangle-v1 lifecycle-sim 0)
    add_cg_behavior_test(lifecycle-07-frame-debugging
                         07-frame-debugging lifecycle-and-workloads lifecycle-sim 0)
    if(CG_GPU STREQUAL "required")
      add_cg_behavior_test(gpu-06-first-frame
                           06-gpu-first-frame shared-textured-triangle-v1 sdl-gpu 0)
      add_cg_behavior_test(gpu-08-renderer-capstone
                           08-renderer-capstone shared-textured-triangle-v1 sdl-gpu 0)
      set_tests_properties(
        gpu-06-first-frame gpu-08-renderer-capstone
        PROPERTIES RESOURCE_LOCK cg_sdl_gpu TIMEOUT 60
      )
    endif()
  elseif(CG_IMPLEMENTATION STREQUAL "starter")
    add_cg_behavior_test(starter-01-not-implemented
                         01-transform-trace identity-triangle software 3)
    add_cg_behavior_test(starter-02-not-implemented
                         02-sampling-and-color corner-marker software 3)
    add_cg_behavior_test(starter-03-not-implemented
                         03-triangle-coverage shared-edge-rectangle software 3)
    add_cg_behavior_test(starter-04-not-implemented
                         04-perspective-depth-blend perspective-checker software 3)
    add_cg_behavior_test(starter-05-not-implemented
                         05-textured-lit-scene textured-lit-scene software 3)
    add_cg_behavior_test(starter-06-not-implemented
                         06-gpu-first-frame shared-textured-triangle-v1 lifecycle-sim 3)
    add_cg_behavior_test(starter-07-not-implemented
                         07-frame-debugging lifecycle-and-workloads lifecycle-sim 3)
    add_cg_behavior_test(starter-08-not-implemented
                         08-renderer-capstone shared-textured-triangle-v1 lifecycle-sim 3)
  endif()
endif()

message(STATUS "CG_IMPLEMENTATION=${CG_IMPLEMENTATION}")
message(STATUS "CG_GPU=${CG_GPU}; CG_HAS_SDL3=${CG_HAS_SDL3}")
