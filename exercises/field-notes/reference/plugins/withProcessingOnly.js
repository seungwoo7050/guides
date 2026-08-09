const { withInfoPlist } = require("expo/config-plugins");

/**
 * expo-task-manager's generic plugin adds legacy `fetch`. Field Notes uses the
 * SDK 57 BGProcessing path only, so remove every unrelated background mode
 * after dependency plugins have run.
 */
module.exports = function withProcessingOnly(config) {
  return withInfoPlist(config, (next) => {
    next.modResults.UIBackgroundModes = ["processing"];
    return next;
  });
};
