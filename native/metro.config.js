const path = require('path');
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');
const workspaceRoot = path.resolve(__dirname, '..');
const qaBuild = process.env.NUTRISOLE_QA === '1';
const nativePackages = ['react', 'react-native', 'react-native-svg', 'react-native-safe-area-context', 'lucide-react-native', '@react-native-async-storage/async-storage'];
module.exports = mergeConfig(getDefaultConfig(__dirname), {
  watchFolders: [workspaceRoot],
  maxWorkers: 2,
  resolver: {
    nodeModulesPaths: [path.join(__dirname, 'node_modules'), path.join(workspaceRoot, 'node_modules')],
    resolveRequest: (context, moduleName, platform) => {
      const requested = nativePackages.some(name => moduleName === name || moduleName.startsWith(name + '/'))
        ? path.join(__dirname, 'node_modules', moduleName) : moduleName;
      const resolved = context.resolveRequest(context, requested, platform);
      // G9 Stage J7: QA APK only (NUTRISOLE_QA=1 at bundle time): bundle flags.qa.ts instead of flags.ts. Unset = production, unchanged.
      if (qaBuild && resolved.type === 'sourceFile' && path.resolve(resolved.filePath) === path.join(__dirname, 'src', 'cv', 'device', 'flags.ts')) {
        return { type: 'sourceFile', filePath: path.join(__dirname, 'src', 'cv', 'device', 'flags.qa.ts') };
      }
      if (resolved.type === 'sourceFile' && path.resolve(resolved.filePath) === path.join(workspaceRoot, 'src', 'nutrisole', 'primitives.native.ts')) {
        return { type: 'sourceFile', filePath: path.join(__dirname, 'touchPrimitives.tsx') };
      }
      return resolved;
    },
  },
});
