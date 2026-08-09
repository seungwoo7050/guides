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
  if(CG_IMPLEMENTATION STREQUAL "reference")
    add_test(
      NAME reference-transform-smoke
      COMMAND cg_render --stage 01-transform-trace --scene identity-triangle
              --backend software --out "${CMAKE_CURRENT_BINARY_DIR}/smoke-out"
    )
  else()
    add_test(
      NAME starter-not-implemented
      COMMAND cg_render --stage 01-transform-trace --scene identity-triangle
              --backend software --out "${CMAKE_CURRENT_BINARY_DIR}/smoke-out"
    )
    set_tests_properties(starter-not-implemented PROPERTIES WILL_FAIL TRUE)
  endif()
endif()

message(STATUS "CG_IMPLEMENTATION=${CG_IMPLEMENTATION}")
message(STATUS "CG_GPU=${CG_GPU}; CG_HAS_SDL3=${CG_HAS_SDL3}")
