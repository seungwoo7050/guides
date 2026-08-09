#include "cg/artifact.hpp"
#include "cg/contracts.hpp"

#include <exception>
#include <iostream>

int main(const int argc, char** argv) {
  try {
    const cg::RunOptions options = cg::parse_arguments(argc, argv);
    cg::validate_new_output_path(options.output);
    const int value = static_cast<int>(options.stage);
    if (value <= static_cast<int>(cg::Stage::sampling_color)) return cg::run_visual_stage(options);
    if (value <= static_cast<int>(cg::Stage::textured_lit_scene)) return cg::run_raster_stage(options);
    return cg::run_gpu_stage(options);
  } catch (const std::invalid_argument& error) {
    std::cerr << "USAGE_ERROR " << error.what() << '\n';
    return cg::exit_usage;
  } catch (const std::exception& error) {
    std::cerr << "CONTRACT_ERROR " << error.what() << '\n';
    return cg::exit_contract_failure;
  }
}
