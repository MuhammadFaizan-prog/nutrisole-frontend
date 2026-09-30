const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');
const config = getDefaultConfig(__dirname);
const workspaceRoot = path.resolve(__dirname, '..');
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [path.join(__dirname, 'node_modules'), path.join(workspaceRoot, 'node_modules')];
// Nested Expo dependencies remain resolvable; shared screens use one native React.
config.resolver.resolveRequest = (context, moduleName, platform) => {
  const requested = moduleName === 'react' || moduleName.startsWith('react/')
    ? path.join(__dirname, 'node_modules', moduleName)
    : moduleName;
  return context.resolveRequest(context, requested, platform);
};
module.exports = config;
