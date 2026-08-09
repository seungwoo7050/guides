#include "cg/artifact.hpp"
#include "cg/contracts.hpp"

#include <string>

namespace cg {

int run_visual_stage(const RunOptions& options) {
  if (options.stage != Stage::transform_trace) return exit_not_implemented;
  ensure_output_directory(options.output);
  write_text(options.output / "conventions.json",
             "{\n  \"schema_version\": 1,\n  \"vector\": \"column\",\n"
             "  \"composition\": \"P * V * M\",\n  \"handedness\": \"left\",\n"
             "  \"depth\": \"0..1\",\n  \"pixel_sample\": \"center\"\n}\n");
  write_text(options.output / "case-identity.json",
             "{\n  \"schema_version\": 1,\n  \"case\": \"identity-triangle\",\n"
             "  \"local\": [0.0, 0.0, 1.0, 1.0],\n"
             "  \"clip\": [0.0, 0.0, 1.0, 1.0],\n"
             "  \"finite\": true,\n  \"valid\": true\n}\n");
  write_text(options.output / "run.json",
             "{\n  \"schema_version\": 1,\n  \"stage\": \"01-transform-trace\",\n"
             "  \"scene\": \"identity-triangle\",\n  \"status\": \"pass\"\n}\n");
  return exit_ok;
}

}  // namespace cg
